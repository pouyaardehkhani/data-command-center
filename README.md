# Data Command Center — website

This branch holds the static marketing site for [Data Command Center](https://github.com/pouyaardehkhani/data-command-center), published with GitHub Pages at:

https://pouyaardehkhani.github.io/data-command-center/

It's plain HTML/CSS/JS (no build step). To preview locally, just open `index.html` in a browser, or serve the folder:

```powershell
python -m http.server 8000
```

## Structure

```
index.html              # the whole site (single page)
assets/css/style.css    # styles (palette mirrors the app's own dark/light theme)
assets/js/main.js       # theme toggle, mobile nav, screenshot lightbox/filters
assets/img/             # logo, favicons, og-image, screenshots
robots.txt, sitemap.xml # SEO
site.webmanifest        # PWA metadata / icons
.nojekyll                # tells GitHub Pages to serve files as-is
```

The app's source code lives on the `main` branch.
