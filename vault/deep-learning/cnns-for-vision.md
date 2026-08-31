# CNNs for Vision

A convolution slides a small filter across an image, detecting a local pattern -
an edge, a corner, a texture - wherever it appears.

Two properties that matter:
- **Parameter sharing** - the same filter is reused across the whole image, so
  a CNN needs far fewer weights than a dense network on pixels
- **Translation invariance** - a cat in the corner is still a cat

Early layers learn edges, deeper layers learn shapes, then objects. That
hierarchy is visible if you plot the filters, and it is the most convincing
thing I have seen about what networks actually learn.

Related: [[Project 2 - Image Classifier]], [[Training Tricks]]
