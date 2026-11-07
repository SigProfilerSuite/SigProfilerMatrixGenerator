# Synthetic Koh classifier fixtures

`koh_indels_oracle.tsv`: 476 synthetic events, one per ID476 channel and covering
all ID89 channels, with independently computed reference labels.

`koh_id89_channels.txt` and `koh_id476_channels.txt`: independently checked
channel order, including open upper bins.

See `reference_data/indel_taxonomy/README.md` for exact upstream commits,
attribution and oracle adaptations. No patient/cohort data is included.
The Python tests use these fixtures directly and never install R dependencies
or access the network.
