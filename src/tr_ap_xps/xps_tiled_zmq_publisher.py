import asyncio
import logging
import os
import re
from datetime import datetime
from uuid import uuid4

import msgpack
import numpy as np
import pytz
import zmq
import zmq.asyncio
from arroyopy.publisher import Publisher
from arroyosas.schemas import RawFrameEvent, SASStart, SASStop, SerializableNumpyArrayModel
from tiled.client import from_uri
from tiled.client.array import ArrayClient
from tiled.client.node import Container
from zmq.asyncio import Context, Socket

from .schemas import XPSResult, XPSResultStart, XPSResultStop

logger = logging.getLogger(__name__)

LOCAL_TILED_API_KEY = os.getenv("RESULTS_TILED_API_KEY") or None
CALIFORNIA_TZ = pytz.timezone("US/Pacific")
UUID_PATTERN = re.compile(
    r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
)
ARRAY_KEY = "xps_averaged_heatmaps"


def extract_uuid(scan_name: str) -> str | None:
    """Extract a UUID36 from a scan_name string.

    Args:
        scan_name: Scan name that may contain a UUID36 substring.

    Returns:
        The matched UUID string, or None if not found.
    """
    match = UUID_PATTERN.search(scan_name)
    return match.group() if match else None


def build_tiled_url(
    tiled_uri: str,
    tiled_prefix: str | None,
    root_segments: list[str],
    uuid: str,
    shot_index: int,
    height: int,
    width: int,
) -> str:
    """Construct the Tiled array slice URL for a single xps_averaged_heatmaps frame.

    Path structure:
        [tiled_prefix /] <root_segments> / <YYYY> / <MM> / <DD> / <uuid> / xps_averaged_heatmaps

    Date is the current date in US/Pacific timezone at call time.

    Args:
        tiled_uri: Base URI of the Tiled server (e.g. ``"http://tiled:8000"``).
        tiled_prefix: Optional top-level container prefix.
        root_segments: Intermediate path segments between prefix and date.
        uuid: UUID extracted from scan_name, used as the container key.
        shot_index: Zero-based index of the shot frame to slice.
        height: Number of rows (detector height).
        width: Number of columns (detector width).

    Returns:
        Full Tiled array URL with slice query parameter.
    """
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


class XPSTiledResultPublisher(Publisher):
    """Publisher that writes XPS shot_mean frames to local Tiled and then
    forwards each written frame as a SAS-style RawFrameEvent to downstream publishers.

    Sequence per XPSResult:
        1. Write (or patch) ``shot_mean`` into the local Tiled server.
        2. Build the exact slice URL for the frame that was just written.
        3. Publish a ``RawFrameEvent`` carrying that URL downstream
           (e.g. to a ZMQFramePublisher wired in the same block).

    Container path structure:
        [tiled_prefix /] <root_segments> / <YYYY> / <MM> / <DD> / <uuid> / xps_averaged_heatmaps

    Args:
        tiled_uri: Base URI of the Tiled server (e.g. ``"http://tiled:8000"``).
        tiled_api_key: API key for Tiled authentication. Falls back to the
            ``RESULTS_TILED_API_KEY`` environment variable when omitted.
        tiled_prefix: Top-level container key under which all data is written.
        root_segments: Intermediate path segments between prefix and date
            (e.g. ``["xps_processed_images"]``).
    """

    def __init__(
        self,
        zmq_socket: Socket,
        tiled_uri: str,
        tiled_api_key: str | None = None,
        tiled_prefix: str | None = None,
        root_segments: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.zmq_socket = zmq_socket
        self.tiled_uri = tiled_uri
        self.tiled_api_key = tiled_api_key or LOCAL_TILED_API_KEY
        self.tiled_prefix = tiled_prefix
        self.root_segments = root_segments or []

        # Tiled state
        self._tiled_client: Container | None = None
        self._array_clients: dict[str, ArrayClient] = {}

        # Per-scan state
        self._current_uuid: str | None = None
        self._current_scan_name: str | None = None
        self._shot_index: int = 0
        self._sas_start_sent: bool = False
        self._scan_started: bool = False  # True only after XPSResultStart received

        logger.info(
            f"Initialized XPSTiledResultPublisher — tiled_uri={tiled_uri}, "
            f"prefix={tiled_prefix}, root_segments={self.root_segments}"
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Connect to the Tiled server eagerly so errors surface at startup."""
        await asyncio.to_thread(self._connect_tiled)

    def _connect_tiled(self) -> None:
        """Open a synchronous Tiled client connection."""
        logger.info(f"Connecting to Tiled server at {self.tiled_uri}")
        self._tiled_client = from_uri(self.tiled_uri, api_key=self.tiled_api_key)

    async def _send_zmq(self, message: SASStart | SASStop | RawFrameEvent) -> None:
        """Serialize a SAS message and send it over ZMQ.

        Args:
            message: A SASStart, SASStop, or RawFrameEvent to serialize and send.
        """
        try:
            if isinstance(message, (SASStart, SASStop)):
                await self.zmq_socket.send(
                    msgpack.packb(message.model_dump(), use_bin_type=True)
                )
            elif isinstance(message, RawFrameEvent):
                await self.zmq_socket.send(
                    msgpack.packb(message.model_dump(), use_bin_type=True)
                )
            else:
                logger.warning(f"Unknown message type for ZMQ send: {type(message)}")
        except Exception as e:
            logger.error(f"Error sending ZMQ message: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # Publisher entry point
    # ------------------------------------------------------------------

    async def publish(
        self, message: XPSResultStart | XPSResult | XPSResultStop
    ) -> None:
        """Route incoming messages to the appropriate handler.

        Args:
            message: One of XPSResultStart, XPSResult, or XPSResultStop.
        """
        if isinstance(message, XPSResultStart):
            await self._handle_start(message)
        elif isinstance(message, XPSResult):
            await self._handle_event(message)
        elif isinstance(message, XPSResultStop):
            await self._handle_stop(message)
        else:
            logger.warning(f"Unhandled message type: {type(message)}")

    # ------------------------------------------------------------------
    # Message handlers
    # ------------------------------------------------------------------

    async def _handle_start(self, message: XPSResultStart) -> None:
        """Reset per-scan state.

        Args:
            message: The XPSResultStart message.
        """
        self._current_scan_name = message.scan_name
        self._current_uuid = extract_uuid(message.scan_name or "")
        self._array_clients = {}
        self._shot_index = 0
        self._sas_start_sent = False
        self._scan_started = True  # mark scan as active; frames before this are discarded

        if self._current_uuid is None:
            self._current_uuid = str(uuid4())
            logger.warning(
                f"No UUID found in scan_name='{message.scan_name}' — "
                f"generated new UUID: '{self._current_uuid}'"
            )
        else:
            logger.info(
                f"Start received — scan_name='{self._current_scan_name}', "
                f"uuid='{self._current_uuid}'"
            )

    async def _handle_event(self, message: XPSResult) -> None:
        """Write shot_mean to Tiled, then publish a RawFrameEvent downstream.

        Steps:
            1. Validate shot_mean shape and UUID presence.
            2. Write or patch the frame into the Tiled array.
            3. Build the slice URL for the frame that was just written.
            4. Publish a SASStart (first frame only), then a RawFrameEvent downstream.

        Args:
            message: The XPSResult message containing shot_mean.
        """
        # Guard: discard frames that arrive before a start message is received.
        # This handles the case where splash_timepix begins emitting before
        # arroyoXPS is ready — those early frames must not be written to Tiled
        # because the reader will request slice indices starting from 0 and any
        # gap will cause slice-not-found errors.
        if not self._scan_started:
            logger.warning(
                f"Received scan '{self._current_scan_name}' frame {message.frame_number} "
                "but no start message has been received yet — discarding frame to avoid "
                "Tiled index desync."
            )
            return

        if message.shot_mean is None:
            logger.debug("shot_mean is None — skipping frame")
            return

        if self._current_uuid is None:
            logger.error("No valid UUID for current scan — ignoring frame")
            return

        shot_array: np.ndarray = message.shot_mean.array

        if shot_array.ndim != 2:
            logger.warning(
                f"Expected 2-D shot_mean, got shape {shot_array.shape} — skipping"
            )
            return

        # Send SASStart on first frame so width/height/data_type are known
        if not self._sas_start_sent:
            try:
                await self._send_zmq(
                    SASStart(
                        run_name=self._current_scan_name or "",
                        run_id=self._current_uuid,
                        tiled_url=self.tiled_uri,
                        width=shot_array.shape[1],
                        height=shot_array.shape[0],
                        data_type=str(shot_array.dtype),
                    )
                )
                self._sas_start_sent = True
            except Exception as e:
                logger.error(f"Error publishing SASStart downstream: {e}", exc_info=True)

        # --- Step 1: write to Tiled ---
        written_index = self._shot_index  # capture before incrementing
        try:
            array_client = await asyncio.to_thread(
                self._get_or_create_array_client, self._current_uuid, shot_array
            )
            if array_client is None:
                logger.warning(f"Failed to get array client for frame {message.frame_number}")
                return

            # Frame 0 was already written by _get_or_create_array_client via write_array
            if written_index > 0:
                await asyncio.to_thread(self._patch_array, array_client, shot_array)
                logger.debug(
                    f"Patched {ARRAY_KEY} for uuid='{self._current_uuid}', "
                    f"shot_index={written_index}"
                )
            else:
                logger.info(f"Initialised {ARRAY_KEY} for uuid='{self._current_uuid}'")

            self._shot_index += 1
        except Exception as e:
            logger.error(
                f"Error writing shot_mean for frame {message.frame_number}: {e}",
                exc_info=True,
            )
            return  # don't forward a URL for a frame that wasn't written

        # --- Step 2: build URL from the frame we just wrote ---
        tiled_url = build_tiled_url(
            tiled_uri=self.tiled_uri,
            tiled_prefix=self.tiled_prefix,
            root_segments=self.root_segments,
            uuid=self._current_uuid,
            shot_index=written_index,
            height=shot_array.shape[0],
            width=shot_array.shape[1],
        )

        # --- Step 3: publish RawFrameEvent downstream ---
        try:
            await self._send_zmq(
                RawFrameEvent(
                    image=SerializableNumpyArrayModel(array=shot_array),
                    frame_number=message.frame_number if message.frame_number is not None else written_index,
                    tiled_url=tiled_url,
                )
            )
            logger.debug(
                f"Published RawFrameEvent downstream — uuid='{self._current_uuid}', "
                f"shot_index={written_index}, tiled_url={tiled_url}"
            )
        except Exception as e:
            logger.error(
                f"Error publishing RawFrameEvent for frame {message.frame_number}: {e}",
                exc_info=True,
            )

    async def _handle_stop(self, message: XPSResultStop) -> None:
        """Publish a SASStop downstream and clear per-scan state.

        Args:
            message: The XPSResultStop message.
        """
        logger.info(
            f"Stop received — clearing state for scan='{self._current_scan_name}', "
            f"uuid='{self._current_uuid}'"
        )

        try:
            await self._send_zmq(SASStop(num_frames=self._shot_index))
        except Exception as e:
            logger.error(f"Error publishing SASStop downstream: {e}", exc_info=True)

        self._array_clients = {}
        self._current_scan_name = None
        self._current_uuid = None
        self._shot_index = 0
        self._sas_start_sent = False
        self._scan_started = False  # reset; next frames must wait for a new start

    # ------------------------------------------------------------------
    # Tiled helpers (synchronous — called via asyncio.to_thread)
    # ------------------------------------------------------------------

    def _get_or_create_array_client(
        self, uuid: str, first_shot: np.ndarray
    ) -> ArrayClient | None:
        """Get a cached array client for uuid, or create the container hierarchy and
        write the initial frame if this is the first time we've seen this uuid.

        Path: [tiled_prefix /] <root_segments> / <YYYY/MM/DD> / <uuid> / xps_averaged_heatmaps

        Args:
            uuid: UUID extracted from scan_name.
            first_shot: 2-D shot_mean array of shape ``(height, width)``. Only used
                on the first call for this uuid to initialise the array shape.

        Returns:
            ArrayClient pointing at the array, or None on error.
        """
        if uuid in self._array_clients:
            return self._array_clients[uuid]

        if self._tiled_client is None:
            logger.error("Tiled client is not connected. Call start() first.")
            return None

        try:
            container: Container = self._tiled_client

            if self.tiled_prefix:
                for segment in self.tiled_prefix.split("/"):
                    if segment:
                        container = self._get_or_create_container(segment, container)

            for segment in self.root_segments:
                container = self._get_or_create_container(segment, container)

            now = datetime.now(CALIFORNIA_TZ)
            for segment in [str(now.year), f"{now.month:02d}", f"{now.day:02d}"]:
                container = self._get_or_create_container(segment, container)

            container = self._get_or_create_container(uuid, container)

            initial_array = first_shot[None, :, :]
            logger.info(
                f"Creating {ARRAY_KEY} for uuid='{uuid}' with shape {initial_array.shape}"
            )
            array_client = container.write_array(initial_array, key=ARRAY_KEY)
            self._array_clients[uuid] = array_client
            return array_client

        except Exception as e:
            logger.error(
                f"Error creating array client for uuid='{uuid}': {e}", exc_info=True
            )
            return None

    def _get_or_create_container(self, key: str, parent: Container) -> Container:
        """Return the child container at key, creating it if absent.

        Args:
            key: Container key to look up or create.
            parent: Parent Tiled container.

        Returns:
            The existing or newly-created child container.
        """
        if key in parent:
            return parent[key]
        logger.info(f"Creating container: {key}")
        return parent.create_container(key)

    def _patch_array(self, array_client: ArrayClient, array: np.ndarray) -> None:
        """Append a new 2-D frame to the existing 3-D Tiled array.

        Args:
            array_client: The ArrayClient to patch into.
            array: 2-D shot_mean array of shape ``(height, width)``.
        """
        current_shape = array_client.shape  # (n_shots, height, width)
        offset = (current_shape[0],)
        logger.debug(f"Patching at offset {offset}, current shape {current_shape}")
        array_client.patch(array[None, :, :], offset=offset, extend=True)
        logger.debug(f"Patch complete — new shape {array_client.shape}")


def xps_tiled_result_publisher_factory(
    zmq_address: str,
    tiled_uri: str,
    tiled_prefix: str | None = None,
    root_segments: list[str] | None = None,
) -> XPSTiledResultPublisher:
    """Instantiate XPSTiledResultPublisher for YAML-based wiring.

    Args:
        zmq_address: ZMQ address to bind and publish SAS messages to
            (e.g. ``"tcp://0.0.0.0:5000"``).
        tiled_uri: Base URI of the Tiled server.
        tiled_prefix: Optional top-level container prefix.
        root_segments: Intermediate path segments between prefix and date.

    Returns:
        A configured XPSTiledResultPublisher instance.
    """
    context = Context()
    zmq_socket = context.socket(zmq.PUB)
    zmq_socket.bind(zmq_address)
    logger.info(f"ZMQ publisher bound to {zmq_address}")
    return XPSTiledResultPublisher(
        zmq_socket=zmq_socket,
        tiled_uri=tiled_uri,
        tiled_prefix=tiled_prefix,
        root_segments=root_segments,
    )