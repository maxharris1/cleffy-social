# cleffy-social

Posts the Cleffy Instagram Reels on schedule, with music from Instagram's library.

- `posts.json`: the calendar (time in Eastern, video, caption, planned track). Built from `feed-v4` with `tools/build_posts.py`.
- `reels/`: the videos (1080x1920, 9 s, silent audio track).
- `post_reel.py`: posts the next due Reel. It checks every 15 minutes, never posts a slot more than 6 hours late, and won't post without music.
- `state/posted.json`: what has gone out. The workflow commits it after each post.
- Secret `IG_PAGE_TOKEN`: the Cleffy Facebook Page token. Never commit it.

Manual run: Actions > Post Reels > Run workflow. Dry run is on by default; set a calendar number to post that one now.
