# Limitations

What Night Sky Finder does not do well yet, so you know when to double-check.

## What I tested

- **Meteor or not:** checked against experts on 200 NightSkyUCP clips (5 experts per clip) and 33 AllSky7 clips (named by the network).
- **The type (plane, satellite, bird, aurora, ...) is not checked by experts.** The datasets only say "meteor" or "not a meteor", so the type is the AI's best guess.
- **The AllSky7 test is small and not blind.** Some of those 33 clips were also used while I improved the code.

## Clips it finds hard

- **Fireballs in twilight or daylight.** On a bright sky the streak is faint and looks slow, so it is often called a plane.
- **Satellite trains** (several satellites one after another on the same path) can be mistaken for space junk burning up.
- **Red sprites** (flashes above thunderstorms) are not recognised.
- **Cloudy or moonlit skies.** Moving clouds and moon glare can hide the object or add false movement.
- **Objects at the very edge of a round (fisheye) camera** are half hidden, so answers there are less sure.
- **Two objects at the same time.** The code follows one moving object per frame, so two objects together can get mixed.

## How it works

- **Answers can change between runs on unclear clips.** Every click asks the AI again (nothing is saved), and the AI does not always pick the same answer when a clip is unclear. Clear clips stay stable.
- **Speed is "% of the screen per second", not km/s.** Real speed needs camera details (lens, position) that the clips don't have.
- **Long videos are sampled.** The code looks at up to 300 frames, so in a long video it skips frames. A very short flash in a long video can be missed.
- **Uploads up to 50 MB.**
- **Tested on a few camera types** (AllSky7, NightSkyUCP, IAC/STARS4ALL, SkySentinel). Other cameras may behave differently.

## The live demo

- **One clip at a time.** The server is small, so other clicks wait their turn. A clip can take from a few seconds up to about a minute.