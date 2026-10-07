HermesLink component licenses and attribution
============================================

HermesLink combines, modifies, and links open-source components including
Hermes Agent, Hermes WebUI, Blink Shell, a-Shell, CPython, iSH, and ios_system.
The repository contains HermesLink integration/glue code and component
customizations; upstream source is fetched at the pinned revisions described
in `blink/UPSTREAM_REVISION` and `scripts/hermes/build/`.

The HermesLink-specific glue code and modifications in this repository were
generated with AI assistance. See `AUTHORS` for the project's authorship
statement. That statement does not replace upstream copyright notices,
licenses, or attribution.

## Component licenses

The links below point to the original license texts or license files at the
upstream source. Where HermesLink pins a revision, the link identifies that
revision.

| Component | License | Original license |
| --- | --- | --- |
| Hermes Agent (`NousResearch/hermes-agent`) | MIT License | [Pinned LICENSE](https://github.com/NousResearch/hermes-agent/blob/2246c245f51e03eb6a151d19119009156e84659a/LICENSE) |
| Hermes WebUI (`nesquena/hermes-webui`) | MIT License | [Pinned LICENSE](https://github.com/nesquena/hermes-webui/blob/e36f77389191fe9d81cd3a7416772e2f7b022e19/LICENSE) |
| Blink Shell (`blinksh/blink`) | GNU GPL version 3 with Blink Additional Terms | [Pinned COPYING](https://github.com/blinksh/blink/blob/a90b4423c8b7a86770c24a7eaa6c13b0a5904b18/COPYING) · [GPLv3 text](https://www.gnu.org/licenses/gpl-3.0.html) |
| a-Shell | BSD 3-Clause License | [Upstream LICENSE](https://github.com/holzschu/a-shell/blob/master/LICENSE) |
| a-Shell-commands (on-demand WASM downloads) | BSD 3-Clause repository license; individual command sources may have separate licenses | [Upstream repository](https://github.com/holzschu/a-Shell-commands) |
| Wasmer JavaScript WASI runtime (`@wasmer/wasi` and `@wasmer/wasmfs` 0.10.2) | MIT License; generated browser bundles retain Microsoft Apache-2.0 notices | `blink/overlay/Resources/WasmRuntime/THIRD_PARTY_NOTICES.txt` |
| CPython (`python/cpython`) | Python Software Foundation License Version 2 | [CPython 3.13.9 LICENSE](https://github.com/python/cpython/blob/v3.13.9/LICENSE) |
| iSH (`ish-app/ish`) | GNU GPLv3 and iSH's additional iOS terms; the upstream source also identifies GPLv2-licensed contributions | [Pinned LICENSE.md](https://github.com/ish-app/ish/blob/83348361fe65311f6e87ad2e1cbb0ac38d123f69/LICENSE.md) · [Pinned LICENSE.IOS](https://github.com/ish-app/ish/blob/83348361fe65311f6e87ad2e1cbb0ac38d123f69/LICENSE.IOS) · [GPLv3 text](https://www.gnu.org/licenses/gpl-3.0.html) |
| ios_system (Blink's pinned `yury/ios_system` submodule) | BSD 3-Clause License | [Pinned submodule LICENSE](https://github.com/yury/ios_system/blob/61f51bed3ec03d2620c6a815e222d945aac976e1/LICENSE) |

Blink's pinned submodule is `yury/ios_system`; it is not a submodule named
`a-Shell/ios_system`. The a-Shell row identifies the upstream a-Shell project
requested for attribution, while the ios_system row identifies the exact
ios_system source recorded by the pinned Blink checkout.

These are project-level license references, not an exhaustive inventory of
licenses for every transitive dependency or vendored file. Third-party notices
and per-file licenses remain applicable and must be preserved when distributing
the resulting app.

For the GPLv3 text used by HermesLink's project-specific code, see the
[GNU GPLv3](https://www.gnu.org/licenses/gpl-3.0.html). This notice does not
purport to relicense upstream code.
