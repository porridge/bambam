# Creating extensions

**Note:** As of bambam version 1.3.0 extension support is an **experimental** feature.
- Details are subject to change.
- There are rough edges and very little validation for correctness.

This document explains how to create a new extension.

## Extension structure

A bambam extension is a directory, containing:
- a mandatory `event_map.yaml` file, and
- some optional media files

  As of version 1.3.0, the only supported files are `wav` and `ogg` sound files. Future versions are likely to add support for image files too.

It is recommended to store sound files in a subdirectory named `sounds`, but this is currently not enforced.

The name of the extension is the name of its directory.

## Event map file

### Example

Here is an example `event_map.yaml` file:

```yaml
apiVersion: 0
image:
- check:
  - type: KEYDOWN
  - unicode:
      isalpha: True
  policy: font

- check:
  - type: KEYDOWN
  - unicode:
      isdigit: True
  policy: font

- policy: random

sound:
- check:
  - unicode:
      value: "0"
  policy: named_file
  args: ["0.ogg"]

- check:
  - unicode:
      value: "1"
  policy: named_file
  args: ["1.ogg"]

- policy: random
```

### Event map structure

This file contains the following top-level fields:
- `apiVersion`: declares the version of the syntax of the file. This field is mandatory and the only supported version is currently `0`
- `image`: event map for images. This field is optional.
- `sound`: event map for sounds. This field is optional.

Both `image` and `sound` fields contain a list of event mapping steps.
During game execution, when an event happens, the steps in *both* lists
are processed (independently) in the order they are specified in this file, until one matches.
If no step matches the event, an error is raised.

### Event mapping steps

A single event mapping step contains the following fields:
- `check` - an optional list of checks.
- `policy` - a mandatory name of reaction selection policy.
- `args` - an optional list of arguments for policy invocation.

For a step to match an event, all checks on its list must match.
An empty list of checks always matches any event.

The following checks are currently available:
- `type`: matches if the type of event is the specified type. The only supported type is currently `KEYDOWN`.
- `unicode`: must contain exactly one of the following sub-checks. A `unicode` check matches, if its sub-check matches. The following sub-checks are currently supported  (see example above for the correct usage):
    - `value`: matches if the event is the unicode character specified,
    - `isalpha`: matches if the `isalpha` function called on the event's associated unicode character returns the specified value (`True` or `False`)
    - `isdigit`: matches if the `isdigit` function  called on the event's associated unicode character returns the specified value (`True` or `False`)

### Reaction selection policies

When an event matches a step, the specified reaction selection policy is invoked.
If a list of arguments is specified in the step, they are also passed to the policy.

After the policy runs, processing of the event stops *on the given step list*.

The following reaction selection policies are supported:
- `font`: Only supported for image steps. Displays a [glyph](https://en.wikipedia.org/wiki/Glyph) representing the event's unicode value.
- `random`: Selects a random media file, loaded *from a data directory* (*not* from the extension directory).
- `named_file`: Currently only supported for sound steps. Selects the file specified as the first argument for policy invocation. The file is loaded *from the extension directory*.
   
  It is recommended to store sound files in a subdirectory named `sounds`, but this is currently not enforced.
