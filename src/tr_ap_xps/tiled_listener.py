"""
Tiled-based listener for Block 2.

Watches a Tiled container for new scans written by XPSTiledPublisher (Block 1)
and emits RawFrameEvents downstream so that ZMQFramePublisher can forward them
to LSE.

Design mirrors TiledPollingRedisListener in arroyosas — minimal changes.
"""

import asyncio
import logging
import os
import time
from datetime import datetime

import pytz
from arroyopy.listener import Listener
from arroyopy.operator import Operator
from tiled.client import from_uri
from tiled.client.node import Container

from arroyosas.schemas import RawFrameEvent, SASStart, SASStop, SerializableNumpyArrayModel
from tr_ap_xps.log_utils import setup_logger

setup_logger(
    logging.getLogger("tr_ap_xps"), log_level=os.getenv("LOGGING_LEVEL", "INFO")
)
logging.getLogger("httpx").setLevel(logging.WARNING)

CALIFORNIA_TZ = pytz.timezone("US/Pacific")


def build_tiled_url(
    tiled_uri: str,
    tiled_prefix: str | None,
    root_segments: list[str],
    uuid: str,
    shot_index: int,
    height: int,
    width: int,
) -> str:
    """Construct the Tiled array slice URL for a single xps_averaged_heatmaps frame."""
    now = datetime.now(CALIFORNIA_TZ)
    date_path = f"{now.year}/{now.month:02d}/{now.day:02d}"

    parts: list[str] = []
    if tiled_prefix:
        parts.append(tiled_prefix)
    parts.extend(root_segments)
    parts.append(date_path)
    parts.append(uuid)
    parts.append(ARRAY_KEY)

    array_path = "/".join(parts)
    slice_param = f"{shot_index}:{shot_index + 1},0:{height},0:{width}"
    return f"{tiled_uri}/api/v1/array/full/{array_path}?slice={slice_param}"

logger = logging.getLogger(__name__)

ARRAY_KEY = "xps_averaged_heatmaps"


class TiledNewScanListener(Listener):
    """Polls a Tiled container for new scan UUIDs written by XPSTiledPublisher.

    For each new scan it finds, it emits:
        SASStart → one RawFrameEvent per shot_mean frame → SASStop

    The full container path is resolved lazily each poll cycle so startup
    succeeds even before Block 1 has written any data to Tiled.

    Args:
        operator: Downstream operator to forward messages to.
        tiled_client: Root Tiled Container (top of the server).
        tiled_uri: Base URI of the Tiled server.
        tiled_prefix: Optional top-level path prefix (e.g. "beamlines/bl931/processed").
        root_segments: Path segments after the prefix (e.g. ["xps_processed_images"]).
        poll_interval_sec: Seconds to sleep between checks for new scans.
        frame_poll_interval_sec: Seconds to sleep between checks for new frames.
    """

    def __init__(
        self,
        operator: Operator,
        tiled_uri: str,
        tiled_api_key: str | None = None,
        tiled_prefix: str | None = None,
        root_segments: list[str] | None = None,
        poll_interval_sec: float = 2.0,
        frame_poll_interval_sec: float = 0.5,
        unchanged_cycles_threshold: int = 5,
        seen_scans_file: str = "/tmp/tiled_listener_seen_scans.txt",
    ) -> None:
        self.operator = operator
        self.tiled_uri = tiled_uri.rstrip("/")
        self.tiled_api_key = tiled_api_key
        self.tiled_prefix = tiled_prefix
        self.root_segments = root_segments or []
        self.poll_interval_sec = poll_interval_sec
        self.frame_poll_interval_sec = frame_poll_interval_sec
        self.unchanged_cycles_threshold = unchanged_cycles_threshold
        self.seen_scans_file = seen_scans_file
        self._seen_scans: set[str] = self._load_seen_scans()

    def _load_seen_scans(self) -> set[str]:
        """Load previously seen scan UUIDs from disk."""
        try:
            with open(self.seen_scans_file) as f:
                uuids = {line.strip() for line in f if line.strip()}
                logger.info(f"Loaded {len(uuids)} previously seen scan(s) from {self.seen_scans_file}")
                return uuids
        except FileNotFoundError:
            return set()

    def _save_seen_scans(self) -> None:
        """Persist seen scan UUIDs to disk."""
        try:
            with open(self.seen_scans_file, "w") as f:
                f.write("\n".join(self._seen_scans))
        except Exception as e:
            logger.warning(f"Could not save seen scans: {e}")

    async def start(self) -> None:
        logger.info(
            f"TiledNewScanListener started — tiled_uri={self.tiled_uri}, "
            f"prefix={self.tiled_prefix}, root_segments={self.root_segments}, "
            f"polling every {self.poll_interval_sec}s"
        )
        loop = asyncio.get_running_loop()
        while True:
            try:
                await asyncio.to_thread(self._poll_once, loop)
            except Exception as e:
                logger.exception(f"Error in scan polling loop: {e}")
            await asyncio.sleep(self.poll_interval_sec)

    def _get_todays_scan_container(self) -> Container | None:
        """Navigate to today's date container, returning None if it doesn't exist yet.

        Reconnects to Tiled on each call to bypass client-side container caching —
        without this, newly written UUID containers are invisible to a stale client.
        """
        try:
            # Fresh client each poll — Tiled caches container children in memory
            # so a long-lived client won't see containers created after startup.
            container = from_uri(self.tiled_uri, api_key=self.tiled_api_key)
            if self.tiled_prefix:
                for segment in self.tiled_prefix.split("/"):
                    if segment:
                        container = container[segment]
            for segment in self.root_segments:
                container = container[segment]
            now = datetime.now(CALIFORNIA_TZ)
            for segment in [str(now.year), f"{now.month:02d}", f"{now.day:02d}"]:
                container = container[segment]
            return container
        except KeyError as e:
            logger.debug(f"Scan container path not yet available: {e}")
            return None
        except Exception as e:
            logger.debug(f"Could not resolve scan container: {e}")
            return None

    def _poll_once(self, loop: asyncio.AbstractEventLoop) -> None:
        """Check for new UUID-level containers under today's date; process each one."""
        scans_container = self._get_todays_scan_container()
        if scans_container is None:
            return
        keys = list(scans_container.keys())
        new_keys = [k for k in keys if k not in self._seen_scans]
        if new_keys:
            logger.debug(f"Found {len(new_keys)} new scan(s), {len(self._seen_scans)} already seen")
        for uuid_key in new_keys:
            self._seen_scans.add(uuid_key)
            self._save_seen_scans()
            try:
                scan_container = scans_container[uuid_key]
                self._process_scan(uuid_key, scan_container, loop)
            except Exception as e:
                logger.exception(f"Error processing scan '{uuid_key}': {e}")

    def _process_scan(self, uuid_key: str, scan_container: Container, loop: asyncio.AbstractEventLoop) -> None:
        """Stream all frames from a scan container, then emit stop."""
        try:
            array_client = scan_container[ARRAY_KEY]
        except KeyError:
            logger.warning(f"Scan '{uuid_key}' has no '{ARRAY_KEY}' array — skipping")
            return
        sent_frames: int = 0
        start_sent = False
        unchanged_cycles: int = 0
        height: int | None = None
        width: int | None = None

        logger.info(f"Processing scan '{uuid_key}'")

        while True:
            # Re-fetch array client each cycle — .shape is cached on the object
            # so reusing the same client will not see new frames written by Block 1.
            try:
                array_client = from_uri(self.tiled_uri, api_key=self.tiled_api_key)[
                    tuple(
                        ([s for s in self.tiled_prefix.split("/") if s] if self.tiled_prefix else [])
                        + self.root_segments
                        + [str(datetime.now(CALIFORNIA_TZ).year),
                           f"{datetime.now(CALIFORNIA_TZ).month:02d}",
                           f"{datetime.now(CALIFORNIA_TZ).day:02d}"]
                        + [uuid_key, ARRAY_KEY]
                    )
                ]
            except Exception as e:
                logger.warning(f"Could not re-fetch array client for '{uuid_key}': {e}")
                time.sleep(self.frame_poll_interval_sec)
                continue

            n_available = array_client.shape[0]
            if height is None:
                height, width = array_client.shape[1], array_client.shape[2]

            if not start_sent and n_available > 0:
                start_msg = SASStart(
                    run_name=uuid_key,
                    run_id=uuid_key,
                    tiled_url=array_client.uri,
                    width=width,
                    height=height,
                    data_type=str(array_client.dtype),
                )
                asyncio.run_coroutine_threadsafe(
                    self.operator.process(start_msg), loop
                ).result()
                start_sent = True

            # Emit any new frames
            while sent_frames < n_available:
                frame_array = array_client[sent_frames]
                tiled_url = build_tiled_url(
                    tiled_uri=self.tiled_uri,
                    tiled_prefix=self.tiled_prefix,
                    root_segments=self.root_segments,
                    uuid=uuid_key,
                    shot_index=sent_frames,
                    height=height,
                    width=width,
                )
                raw_event = RawFrameEvent(
                    image=SerializableNumpyArrayModel(array=frame_array),
                    frame_number=sent_frames,
                    tiled_url=tiled_url,
                )
                asyncio.run_coroutine_threadsafe(
                    self.operator.process(raw_event), loop
                ).result()
                sent_frames += 1
                logger.debug(f"Emitted frame {sent_frames - 1} for scan '{uuid_key}'")

            time.sleep(self.frame_poll_interval_sec)
            # Re-fetch after sleep to get the latest frame count from Tiled
            try:
                refreshed = from_uri(self.tiled_uri, api_key=self.tiled_api_key)[
                    tuple(
                        ([s for s in self.tiled_prefix.split("/") if s] if self.tiled_prefix else [])
                        + self.root_segments
                        + [str(datetime.now(CALIFORNIA_TZ).year),
                           f"{datetime.now(CALIFORNIA_TZ).month:02d}",
                           f"{datetime.now(CALIFORNIA_TZ).day:02d}"]
                        + [uuid_key, ARRAY_KEY]
                    )
                ]
                n_after_sleep = refreshed.shape[0]
            except Exception:
                n_after_sleep = n_available

            if n_after_sleep == sent_frames and n_after_sleep > 0:
                unchanged_cycles += 1
                logger.debug(f"No new frames for scan '{uuid_key}' — unchanged cycle {unchanged_cycles}/5")
                if unchanged_cycles >= self.unchanged_cycles_threshold:
                    break
            else:
                unchanged_cycles = 0

        if start_sent:
            asyncio.run_coroutine_threadsafe(
                self.operator.process(SASStop(num_frames=sent_frames)), loop
            ).result()
            logger.info(f"Scan '{uuid_key}' complete — {sent_frames} frames emitted")

    async def stop(self) -> None:
        pass

    async def listen(self) -> None:
        pass

    @classmethod
    def from_settings(cls, settings, operator: Operator) -> "TiledNewScanListener":
        return cls(
            operator=operator,
            tiled_uri=settings.uri,
            tiled_api_key=getattr(settings, "api_key", None),
            tiled_prefix=getattr(settings, "tiled_prefix", None),
            root_segments=settings.root_segments.to_list(),
            poll_interval_sec=getattr(settings, "poll_interval_sec", 2.0),
            frame_poll_interval_sec=getattr(settings, "frame_poll_interval_sec", 0.5),
        )


def tiled_new_scan_listener_factory(
    operator: Operator,
    tiled_uri: str,
    root_segments: list[str],
    tiled_prefix: str | None = None,
    poll_interval_sec: float = 2.0,
    frame_poll_interval_sec: float = 0.5,
    unchanged_cycles_threshold: int = 5,
    seen_scans_file: str = "/tmp/tiled_listener_seen_scans.txt",
) -> TiledNewScanListener:
    """Factory function for YAML-based wiring."""
    tiled_api_key = os.getenv("RESULTS_TILED_API_KEY") or None
    logger.info(f"TiledNewScanListener factory — tiled_uri={tiled_uri}, prefix={tiled_prefix}, root_segments={root_segments}")
    return TiledNewScanListener(
        operator=operator,
        tiled_uri=tiled_uri,
        tiled_api_key=tiled_api_key,
        tiled_prefix=tiled_prefix,
        root_segments=root_segments,
        poll_interval_sec=poll_interval_sec,
        frame_poll_interval_sec=frame_poll_interval_sec,
        unchanged_cycles_threshold=unchanged_cycles_threshold,
        seen_scans_file=seen_scans_file,
    )