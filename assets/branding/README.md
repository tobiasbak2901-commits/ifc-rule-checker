# Ponker Icon Exports

Master source for app icons:
- `assets/branding/ponker_icon_square.svg` (platform/app master, no baked corner rounding)
- `assets/branding/ponker_icon_preview_rounded.svg` (marketing preview with rounded container)

Export PNG sizes from square master:

```bash
mkdir -p assets/branding/exports
for s in 1024 512 256 128 64 32 16; do
  rsvg-convert -w "$s" -h "$s" assets/branding/ponker_icon_square.svg \
    -o "assets/branding/exports/ponker_icon_${s}.png"
done
```

Quick size check:

```bash
identify assets/branding/exports/ponker_icon_*.png
```
