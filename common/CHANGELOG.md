# Changelog — `common/` (the vendored shared helper)

This is the changelog of the **`common/` folder itself**, separate from the
example's own `CHANGELOG.md`. The folder is vendored (copied) into every
example repository in the BACnet profile example series; this file plus the
`COMMON_VERSION` constant in `CASExampleHelper.h` tell you whether a given
example's copy is stale.

**Rule:** any change to anything in `common/` bumps `COMMON_VERSION`, gets an
entry here, and must then be re-copied into **every** example in the series.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the folder adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-07-14

### Added

- `COMMON_VERSION` constant in `CASExampleHelper.h` and this changelog — the
  folder now carries its own version so each example can tell whether its
  vendored copy is stale. `PrintVersion` prints it alongside the app + stack
  versions.
- `CASBACnetStackExampleConstants.h` is now the **series-wide superset**: one
  identical constants file for every example (previously each example carried
  only the constants it used, so the copies drifted). Includes the output
  object types, commandable-property identifiers (`Priority_Array`,
  `Relinquish_Default`), and error codes introduced for B-SA.

## [1.0.1] - 2026-06-16

### Fixed

- `GetPrimaryIPv4` (Windows): check the subnet-mask `inet_pton` return and
  zero-initialize the `in_addr`, so a mask string that fails to parse can no
  longer be read uninitialized (it falls back to the limited broadcast).
  (Shipped in B-SS v1.0.2; the folder was unversioned at the time.)

## [1.0.0] - 2026-06-16

### Added

- Initial vendored helper: `CASExampleHelper` (UDP transport + time callbacks,
  version/help printing, `--port` / `--deviceID` parsing, keyboard commands
  h/q/up/down, local-IPv4 + broadcast lookup, unsolicited I-Am on start-up),
  `SimpleUDP` (cross-platform UDP socket wrapper), and
  `CASBACnetStackExampleConstants.h`.
