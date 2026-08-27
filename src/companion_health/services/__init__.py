"""
Services monitoring for companion health.

Tracks the processes named in the config services list and packs their
running state into the services_status bitmask (bit N = list entry N).
"""

from .monitor import ServicesMonitor

__all__ = ['ServicesMonitor']
