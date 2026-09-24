# TODO
- [ ] Run workflow "Build and Publish ABM v4" with country=IR, force=true, publish=true (old IR.abm has ways=1).
- [ ] On device: delete old IR map data, redownload, confirm log `SQL COUNT ways/segments` >> 1.
- [ ] Implicit oneway not handled in routing/graph_builder.py `_add_way` (junction=roundabout, motorway, motorway_link).
