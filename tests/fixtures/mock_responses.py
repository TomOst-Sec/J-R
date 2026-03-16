"""Pre-built mock HTTP response data for integration tests."""

GITHUB_USER_JOHNDOE = {
    "login": "johndoe",
    "id": 12345,
    "html_url": "https://github.com/johndoe",
    "name": "John Doe",
    "bio": "Software engineer and open source enthusiast",
    "location": "San Francisco, CA",
    "avatar_url": "https://avatars.githubusercontent.com/u/12345",
    "blog": "https://johndoe.dev",
    "created_at": "2018-01-15T00:00:00Z",
    "followers": 150,
    "following": 42,
}

GITHUB_USER_JOHNDOE_REPOS = [
    {
        "id": 100,
        "name": "my-project",
        "description": "A cool project",
        "html_url": "https://github.com/johndoe/my-project",
        "pushed_at": "2025-06-01T10:00:00Z",
        "stargazers_count": 10,
        "forks_count": 2,
    }
]

GITHUB_SEARCH_JOHNDOE = {
    "items": [
        {
            "login": "johndoe",
            "html_url": "https://github.com/johndoe",
        }
    ]
}

REDDIT_USER_JOHNDOE = {
    "kind": "t2",
    "data": {
        "name": "johndoe",
        "subreddit": {
            "public_description": "Software engineer sharing code and ideas",
        },
        "icon_img": "https://styles.redditmedia.com/johndoe.png",
        "created_utc": 1516000000.0,
        "link_karma": 500,
        "comment_karma": 2000,
        "is_suspended": False,
    },
}

REDDIT_USER_JOHNDOE_POSTS = {
    "kind": "Listing",
    "data": {
        "children": [
            {
                "kind": "t3",
                "data": {
                    "id": "r1",
                    "title": "Just shipped my new project",
                    "selftext": "Check it out on GitHub",
                    "created_utc": 1700000000.0,
                    "permalink": "/r/programming/comments/r1/",
                    "ups": 100,
                    "num_comments": 20,
                    "name": "t3_r1",
                },
            }
        ],
    },
}

HACKERNEWS_USER_JOHNDOE = {
    "id": "johndoe",
    "created": 1516000000,
    "karma": 3500,
    "about": "Software engineer. Love building things.",
}

HACKERNEWS_SUBMITTED = [101, 102]

HACKERNEWS_ITEM_101 = {
    "id": 101,
    "type": "story",
    "by": "johndoe",
    "title": "Show HN: My new project",
    "url": "https://johndoe.dev/project",
    "text": "",
    "time": 1700000000,
    "score": 50,
    "descendants": 10,
}

# Profile pair that should NOT match (different person)
GITHUB_USER_JANEDOE = {
    "login": "janedoe",
    "id": 99999,
    "html_url": "https://github.com/janedoe",
    "name": "Jane Doe",
    "bio": "Data scientist and ML researcher",
    "location": "New York, NY",
    "avatar_url": "https://avatars.githubusercontent.com/u/99999",
    "blog": "",
    "created_at": "2020-05-01T00:00:00Z",
    "followers": 30,
    "following": 10,
}

# Seed profile for matching
SEED_PROFILE_GITHUB = {
    "login": "johndoe",
    "name": "John Doe",
    "bio": "Software engineer and open source enthusiast",
    "avatar_url": "https://avatars.githubusercontent.com/u/12345",
}
