# Cyber Bible

Makes the daily reading graphics for Cyfrowa Biblia and publishes them to
Instagram, a Facebook Page and X. See `CLAUDE.md` for how the code is laid out.

## Facebook and X

Publishing to Facebook and X is optional. Until their keys are in `.env` on the
server, their checkboxes next to **Publish** stay greyed out. After editing
`.env`, restart the app (`docker compose up -d`) so it reads the new keys.

### Facebook Page

Posts go out through Meta's Graph API as one multi-photo post on the Page,
with the same images and caption as on Instagram. Meta only allows this for
Pages, not personal profiles. Publishing to a Page you manage yourself needs
no App Review.

1. Go to <https://developers.facebook.com/apps>, **Create app**, and choose the
   use case for managing your Page's content.
2. Open the **Graph API Explorer**, pick your app, choose **User Token**, and
   add the permissions `pages_show_list`, `pages_read_engagement` and
   `pages_manage_posts`. Click **Generate Access Token** and allow access to
   the Cyfrowa Biblia Page.
3. In the **Access Token Debugger**, paste that token and click
   **Extend Access Token** to get a long-lived (about 60-day) user token.
4. Back in the Graph API Explorer, with the long-lived token, run
   `GET me/accounts`. Find your Page and copy its `id` and `access_token`.
   This Page token does not expire. You can check it in the Access Token
   Debugger: it should say "Expires: Never".
5. Put them in `.env`:
   ```
   FACEBOOK_PAGE_ID=<id>
   FACEBOOK_PAGE_TOKEN=<access_token>
   ```
6. **Switch the app to Live** (App settings → Basic needs a Privacy Policy URL
   first). While the app is in Development mode, its posts are visible only to
   you and other app admins, not to your followers.

### X

Posts go out through the official X API. X has no free API tier anymore:
posting is pay-per-use from prepaid credits, roughly $0.015 per post. A day
is a thread of about 2–3 posts, because X allows at most 4 images per post.
The first post has the start of the caption, the date and hashtags, cut to fit
280 characters. The replies carry the rest of the images.

1. Sign in to the X developer console with the **Cyfrowa Biblia X account**
   (posts go out as the account that creates the access token). Create an
   app, then buy some credits under billing.
2. In the app's **User authentication settings**, set App permissions to
   **Read and write** (type: Web App, Automated App or Bot). The callback URL
   and website fields are required; any URL you own works (they're unused).
3. On **Keys and tokens**, copy the **API Key and Secret**, then generate the
   **Access Token and Secret**. If you generated the access token before
   switching to Read and write, regenerate it: old tokens stay read-only.
4. Put all four in `.env`:
   ```
   X_API_KEY=
   X_API_SECRET=
   X_ACCESS_TOKEN=
   X_ACCESS_TOKEN_SECRET=
   ```

### Publishing

Tick the platforms under **Publish** (the choice is remembered in that
browser). Each platform is published separately: if one fails, the others still
go out, and the status lists each result. `web/<date>/_published.json` records
every platform a date went out on. Publishing a date there again asks first;
**Cancel** publishes only to the platforms it hasn't been posted on yet. If an X
reply fails after the first post is live, the day still counts as posted on X,
so a retry doesn't post the whole thread twice.
