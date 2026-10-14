# merchient.com

The website of Merchient, a trade name of Orbline LLC: claims review for US supplement brands running Meta ads. Contact: hello@merchient.com.

It is a static site: plain HTML pages and one stylesheet, with no build step, no scripts, no cookies and no tracking.

## Pages

- `index.html`: the main page
- `connect.html`: how to share a Meta ad account with Merchient, view-only
- `privacy.html`: privacy policy
- `terms.html`: terms of service
- `data-deletion.html`: how to have data deleted and remove Merchient's access in Meta
- `shopify/connected.html`: the page a store owner lands on after connecting a Shopify store
- `404.html`: shown for addresses that do not exist

## How it is published

GitHub Pages serves the `main` branch of this repository, from the root folder, at https://merchient.com, the custom domain set in `CNAME`. The `.nojekyll` file makes GitHub Pages serve the files as they are. Every push to `main` publishes the site.
