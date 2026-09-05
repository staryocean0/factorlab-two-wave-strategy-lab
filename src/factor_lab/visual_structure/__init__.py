"""Visual structure extraction utilities.

These utilities are posterior visual-analysis tools.  They are designed to
extract scale-aware price skeletons for attribution, review, and feature
research, not to provide causal trading signals by themselves.
"""

from factor_lab.visual_structure.endpoint_channel import (
    EndpointAnchor,
    EndpointChannelConfig,
    EndpointChannelResult,
    compute_endpoint_channel,
)

__all__ = [
    "EndpointAnchor",
    "EndpointChannelConfig",
    "EndpointChannelResult",
    "compute_endpoint_channel",
]
