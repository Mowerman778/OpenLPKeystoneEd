# OpenLPUG — Phase 1 bug triage

Sourced from the upstream OpenLP tracker (gitlab.com/openlp/openlp) via the public API, filtered to
real bugs relevant to the fork's focus (stability, Windows, display/media). Feature requests excluded.
Ordered roughly by value × tractability on the Linux dev box (headless, offscreen Qt, no VLC/Windows).

Legend: **[fixable here]** = reproducible + unit-testable offscreen · **[needs Windows/VLC]** = requires
real display or media hardware to verify.

## Data-loss / correctness (high value)
| Issue | Title | Notes | Status |
|-------|-------|-------|--------|
| #2006 / #2146 | `ValueError: Unknown author type: translate` | Legacy alias in real song DBs crashes song edit/render. **[fixable here]** | ✅ FIXED |
| #2186 | Pressing delete on a verse deletes the whole song | Editor selection/shortcut bug. **[fixable here]** | TODO |
| #1995 | Song export ignores checked state | Export selection bug. **[fixable here]** | TODO |
| #2266 | Sometimes shows only 3 lines per slide | Renderer/textFit edge case. **[needs display]** | TODO |

## Crashes / stability
| Issue | Title | Notes | Status |
|-------|-------|-------|--------|
| #2261 | Crashes when I try to save | Needs repro detail. | TODO |
| #2034 | 3.1.7 crash on Windows 11 when window is shrunk | Layout/min-size. **[needs Windows]** | TODO |
| #1323 | RuntimeError: wrapped C/C++ QTreeWidgetItem has been deleted | Lifetime/teardown race. **[fixable here]** | TODO |
| #2200 | macOS crash: remote web interface Bible search | API path. **[fixable here]** | TODO |

## Display / video / media — (also underpins Phase 2 video-behind-lyrics + PiP)
| Issue | Title | Notes | Status |
|-------|-------|-------|--------|
| #1941 | Background video flickering when going live or looping | z-order/translucency. **[needs display+VLC]** | TODO |
| #1245 | DisplayWindow not transparent with video background theme | Translucency toggle. **[needs display]** | TODO |
| #1078 | Background video vanishes when service item has linked audio | Media type routing. **[fixable here?]** | TODO |
| #1568 | No sound on videos | VLC audio track. **[needs VLC]** | TODO |
| #1013 | Blanking a video: audio heard a couple seconds more | Stop/blank ordering. **[fixable here?]** | TODO |
| #1477 | Video replays after end, then output blanked | End-of-media handling. **[fixable here?]** | TODO |
| #1977 | PowerPoints not closed when moving to a new item | Presentation teardown. **[needs Office]** | TODO |

## Other confirmed bugs
| Issue | Title | Notes | Status |
|-------|-------|-------|--------|
| #2011 | Not honoring screen height % in iframe tags | Render tag parsing. **[fixable here]** | TODO |
| #1944 | Windows uses display-screen text size on both screens | Per-screen scaling. **[needs Windows]** | TODO |
| #1499 | Web remote "show black" won't go dark on main view | Blank-state sync. **[fixable here?]** | TODO |
| #1982 | Duplicate song search does not work | Search logic. **[fixable here]** | TODO |

> The **[fixable here]** items are the near-term queue; **[needs Windows/VLC]** items are staged for
> verification on the user's Windows laptop and to be re-tested once video-behind-lyrics work begins.
