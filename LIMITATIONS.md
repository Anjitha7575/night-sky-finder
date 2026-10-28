# Limitations

- Speed is measured in pixels per frame, not km/s. Real speed needs camera details (field of view) that the dataset does not give.
- Test clips are cropped around the object, and crop sizes differ (80x44 to 640x360), so pixel speeds are not fully comparable between clips.
- In the dataset, clip length alone separates meteors from non-meteors about 98% of the time (reported in the original paper). We do not give clip length to the AI.
- The dataset has only meteor / non-meteor labels. There is no satellite label, so satellite results cannot be checked against expert labels.
- Data is from 2019–2021, before the big growth of Starlink satellites.
- Very slow objects (like clouds) are missed when comparing neighbouring frames, so we also compare frames further apart.