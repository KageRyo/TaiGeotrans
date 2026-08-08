# TGOS fixtures

`tgos_queryaddr_exact_match.json` follows the JSON response shape and exact-match
metadata shown in the [TGOS QueryAddr v30 documentation](https://addr.tgos.tw/addrws/v30/QueryAddr.asmx?op=QueryAddr).

The documented example uses `EPSG:3826` output coordinates. This client requests
`EPSG:4326`, so the fixture contains the equivalent WGS84 coordinates for the
same documented address. It contains no AppID or API key.
