import asyncio
import logging
import os
import re
from datetime import datetime
from uuid import uuid4

import numpy as np
import pytz
from arroyopy.publisher import Publisher
from tiled.client import from_uri
from tiled.client.array import ArrayClient
from tiled.client.node import Container

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


class XPSTiledResultPublisher(Publisher):
    """Publisher that writes XPS shot_mean frames to local Tiled.

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
        tiled_uri: str,
        tiled_api_key: str | None = None,
        tiled_prefix: str | None = None,
        root_segments: list[str] | None = None,
    ) -> None:
        super().__init__()
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
        """Write shot_mean to Tiled.

        Args:
            message: The XPSResult message containing shot_mean.
        """
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

        # --- Write to Tiled ---
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

    async def _handle_stop(self, message: XPSResultStop) -> None:
        """Clear per-scan state.

        Args:
            message: The XPSResultStop message.
        """
        logger.info(
            f"Stop received — clearing state for scan='{self._current_scan_name}', "
            f"uuid='{self._current_uuid}'"
        )

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
    tiled_uri: str,
    tiled_prefix: str | None = None,
    root_segments: list[str] | None = None,
) -> XPSTiledResultPublisher:
    """Instantiate XPSTiledResultPublisher for YAML-based wiring.

    Args:
        tiled_uri: Base URI of the Tiled server.
        tiled_prefix: Optional top-level container prefix.
        root_segments: Intermediate path segments between prefix and date.

    Returns:
        A configured XPSTiledResultPublisher instance.
    """
    return XPSTiledResultPublisher(
        tiled_uri=tiled_uri,
        tiled_prefix=tiled_prefix,
        root_segments=root_segments,
    )