# scriptura.wrootpress.com — preliminary findings page

Static, no build. Numbers come from `FINDINGS-preliminary.md` (spine v0 + sensus ledgers, 2026-11-10).
OG image: `og/og.html` rendered to `og.png` (1200x630) with headless Chrome:
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars --window-size=1200,630 --screenshot=$PWD/og.png "file://$PWD/og/og.html"
Deploy (each one = Wilson's OK): `cd site && npx vercel deploy --prod --scope wilson-pruitts-projects`
(Vercel project `scriptura-wrootpress`; Cloudflare CNAME `scriptura` -> `cname.vercel-dns.com`, proxy off).
