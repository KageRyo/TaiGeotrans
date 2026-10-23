# Privacy and Data Handling

**English** | [繁體中文](PRIVACY_ZH.md)

Last updated: 2026-10-13. This notice describes the official TaiGeotrans Python package and CLI as implemented in version 0.1.2. It does not describe a separately hosted application that uses the package.

## Data flow

TaiGeotrans has no built-in telemetry or mechanism that sends addresses, coordinates, results, or usage records to the project maintainers. Its default geocoding requests go to TGOS, without passing through a TaiGeotrans-operated server.

| Operation | Processing and destination |
|---|---|
| WGS84 ↔ TWD97 conversion, including coordinate batches | Computed in the environment running TaiGeotrans using pyproj; does not require TGOS or send input coordinates to it. |
| Address geocoding, including address batches | Sends the submitted address, your TGOS AppID/APIKey, and query parameters to the configured geocoding endpoint; the default destination is TGOS. |
| DataFrame or GeoJSON conversion and CLI output | Formats results in the execution environment; the CLI can display results or write files to a destination you specify. |

The execution environment may be your own computer or a server operated by an application provider. Local processing refers to that environment, not necessarily an end user's device.

## TGOS address geocoding

The default endpoint is `https://addr.tgos.tw/addrws/v30/QueryAddr.asmx/QueryAddr`. Requests use HTTPS GET, with the address, credentials, and query options in URL query parameters. TGOS processes the request and returns matching address information and coordinates. Failed requests may be retried.

The receiving service can also observe connection information, such as the connecting IP address. HTTPS protects the request in transit, but does not hide it from the receiving service or an intermediary configured to decrypt that connection.

Refer to the [TGOS privacy policy](https://www.tgos.tw/tgos/Privacy) and the service terms applicable to your TGOS account and API access. TaiGeotrans does not control TGOS's collection, retention, use, or deletion of data. The linked platform policy should not be read as a guarantee of any particular retention period for address API queries. Direct questions about TGOS-held data to TGOS through its official support channels.

## Results, files, and logs

Results can contain the original address or coordinates, matched addresses, converted coordinates, and error details. TaiGeotrans does not maintain its own persistent query database. Your application, terminal, output files, backups, or hosting platform may retain these values according to their configuration.

Coordinate debug messages, warnings, and errors can include coordinate values. HTTP client logs and exception traces may include request URLs, which can contain addresses and TGOS credentials. The package's own TGOS logging calls do not explicitly print AppID/APIKey values, but this is not a guarantee that credentials cannot appear in logs elsewhere in the execution environment.

Command-line arguments may also remain in shell history or be visible to process-monitoring tools. Review logging and output settings before processing sensitive data; redact addresses, coordinates, credentials, and request URLs before sharing diagnostic material.

## Configuration and applications using TaiGeotrans

An unchanged copy of the package can still behave differently when configured or embedded in another application. `TGOS_API_BASE_URL`, a custom TGOS client or transformer, proxy settings, and application-level logging or monitoring can change where data goes and what is recorded.

If you use a service built with TaiGeotrans, consult that service's privacy notice as well. Its operator determines how submitted data and results are handled outside this package. This notice does not cover modified distributions or independently operated services.

## Credentials and support

Keep TGOS credentials out of source control and shared output. Manage stored input, results, logs, and credentials in the environment you operate; TaiGeotrans does not provide a central account or deletion service for those records.

Do not include real personal addresses, sensitive coordinates, API keys, or unredacted logs in public GitHub issues. Use synthetic or redacted examples. For credential exposure or security vulnerabilities, follow [SECURITY.md](SECURITY.md); revoke exposed TGOS credentials through TGOS.

## Scope and updates

This notice describes package behavior, not the privacy practices of GitHub, PyPI, TGOS, or applications that integrate TaiGeotrans. Visiting those services or installing packages involves their own infrastructure and policies. Changes to TaiGeotrans's data handling should be reflected in this notice and its [Traditional Chinese version](PRIVACY_ZH.md).

Trusted administrative context supplied by a caller is included in the completed address sent to TGOS. Results can retain the original/normalized/completed address, candidate address explanations and a provider-response digest; applications choose whether and where to persist those records.
