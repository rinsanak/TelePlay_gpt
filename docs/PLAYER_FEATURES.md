# Subtitle import, sound boost, and external player selection

Applies to the Android TV/projector and Android mobile players. Deploy the updated
Python backend and rebuild/install the Android app together. No database migration
is needed. The web player is unchanged.

## Behavior

- Player Settings always remains accessible, even with no embedded tracks.
- Add subtitle appears after the embedded subtitle tracks. It lists the latest four
  supported subtitle uploads in the authenticated user's private bot chat across
  folders, then ranks those four by filename similarity. Filenames and sizes are
  shown. Supported suffixes: .srt, .vtt, .ass, .ssa (case-insensitive).
- The app's existing ingestion only handles private messages to its bot. This is
  not a search of arbitrary Telegram groups/channels or unsent local files.
- Select from device storage uses Android's document picker. A compatible document
  provider/file manager must be installed on the projector. Cancel keeps playback
  unchanged. A valid selection replaces the previously imported subtitle and keeps
  the playback position and play/pause state. Off and embedded track selection
  remain available. ASS/SSA rendering follows Media3's supported styling subset.
- Sound boost offers 100/125/150/175/200 percent of nominal signal amplitude.
  Android LoudnessEnhancer handles amplification and peak compression; no source
  file is transcoded. 100% releases the effect. This is not a guarantee of lossless
  amplified sound: peaks can be compressed, and output/device support varies.
- Select external player opens the Android chooser, even if a default app exists.
  It pauses internal playback and passes a 12-hour, file-scoped URL instead of a
  permanent public share or the account access token. Logout-all revokes the URL.
  The current position is supplied as an optional player-specific extra; apps may
  ignore it. Canceling the chooser leaves internal playback paused (press Play).
  External playback requires the backend/network even when a local video copy exists.
  Imported subtitles and internal boost settings are not transferred to other apps.

## Validation completed

`cd backend && python -m unittest discover -s tests -v`: 9 tests passed.
Covers latest-four selection, case/punctuation matching, size, empty results,
user isolation, file-scoped links, expiration, token-type rejection, logout
revocation and absence of permanent public sharing. Python syntax and diff
whitespace checks passed.

Android compilation was attempted but the environment could not download Gradle
(Network is unreachable). No APK or projector/device test was completed. The
included Player checks workflow builds an unsigned-debug-installable universal APK
(signed with the Android debug key), runs Android unit tests, and runs backend tests
on GitHub once pushed. No signing secrets are needed.

## Device checks before release

1. Open a video without embedded subtitles and navigate Settings by D-pad.
2. Upload at least five subtitles to the bot; verify only the newest four appear,
   with the closest filename first and correct sizes. Check empty/error/retry.
3. Import each supported format from Telegram and device storage while playing and
   paused. Check resume position, Unicode text, Off, embedded track switching, retry,
   and canceling the document picker. Test unavailable file-manager behavior.
4. Listen to quiet and loud audio at every boost setting; return to 100%. Check
   output changes (HDMI/Bluetooth), unsupported effects, and opening a second video.
5. Install two media players; verify chooser, streaming, seek, cancel, expired link,
   and logout-all revocation. Playback position support differs between players.
