# Example timing files

These are fictional **reference-clock seconds**, not real episode decisions. `anchors.json` describes matching reference/source events; `turns.json` describes reviewed speaker turns; `keeps.json` describes retained content intervals. Replace all timings with observations from the actual episode. The example turns cover the example keeps, but the manual sync anchors describe an independent demonstration clock.

Initialize a real project with `podcut init`, then edit its generated manifest using docs/WORKFLOW.md. Do not copy fake media paths, probe fields or source fingerprints from a template.

[thumbnail-brief.json](thumbnail-brief.json) is a fictional, agent-owned cover-planning record. Replace its example topic/times, identify real participants, and obtain the actual choices. It has no generated artwork or approval and is not a CLI renderer input. See [the thumbnail workflow](../docs/THUMBNAILS.md).
