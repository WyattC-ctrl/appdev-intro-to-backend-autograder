"""Small Flask apps that stand in for student submissions."""

# A PA1 app. The two constants at the top are replaced for each fixture.
PA1_APP = '''
import json
from flask import Flask, jsonify, request

BROKEN = {broken!r}      # core features that deliberately misbehave
CHALLENGE = {challenge!r}  # challenge features that work

app = Flask(__name__)
posts = {{}}
next_id = [1]


def fail(message, code):
    return jsonify({{"error": message}}), code


def serialize(post):
    return {{k: v for k, v in post.items() if k != "comments"}}


def create(body):
    post = {{
        "id": next_id[0], "upvotes": 1, "title": body.get("title"),
        "link": body.get("link"), "username": body.get("username"), "comments": [],
    }}
    next_id[0] += 1
    posts[post["id"]] = post
    return jsonify(serialize(post)), 201


@app.route("/api/posts/")
def get_posts():
    if "get_posts" in BROKEN:
        return fail("broken", 500)
    return jsonify({{"posts": [serialize(p) for p in posts.values()]}})


@app.route("/api/posts/", methods=["POST"])
def create_post():
    return create(json.loads(request.data))


@app.route("/api/posts/<int:post_id>/")
def get_post(post_id):
    if post_id not in posts:
        return fail("not found", 404)
    return jsonify(serialize(posts[post_id]))


@app.route("/api/posts/<int:post_id>/", methods=["DELETE"])
def delete_post(post_id):
    if "delete" in BROKEN:
        return fail("broken", 500)
    if post_id not in posts:
        return fail("not found", 404)
    return jsonify(serialize(posts.pop(post_id)))


@app.route("/api/posts/<int:post_id>/comments/")
def get_comments(post_id):
    if post_id not in posts:
        return fail("not found", 404)
    return jsonify({{"comments": posts[post_id]["comments"]}})


def add_comment(post_id, body):
    if post_id not in posts:
        return fail("not found", 404)
    comment = {{"id": next_id[0], "text": body.get("text"), "username": body.get("username")}}
    next_id[0] += 1
    posts[post_id]["comments"].append(comment)
    return jsonify(comment), 201


@app.route("/api/posts/<int:post_id>/comments/", methods=["POST"])
def post_comment(post_id):
    return add_comment(post_id, json.loads(request.data))


def edit(post_id, comment_id, body):
    if post_id in posts:
        for comment in posts[post_id]["comments"]:
            if comment["id"] == comment_id:
                comment["text"] = body.get("text")
                return jsonify(comment)
    return fail("not found", 404)


@app.route("/api/posts/<int:post_id>/comments/<int:comment_id>/", methods=["POST"])
def edit_comment(post_id, comment_id):
    if "edit" in BROKEN:
        return fail("broken", 500)
    return edit(post_id, comment_id, json.loads(request.data))


@app.route("/api/extra/posts/", methods=["POST"])
def extra_create():
    body = json.loads(request.data)
    if "tier1" in CHALLENGE and not all(isinstance(body.get(k), str) for k in ("title", "link", "username")):
        return fail("bad", 400)
    link = str(body.get("link"))
    if "strict_url" in CHALLENGE and not link.startswith(("http://", "https://")):
        return fail("bad", 400)
    if "bare_domain_only" in CHALLENGE and "://" in link:
        return fail("bad", 400)
    if "loose_url" in CHALLENGE and "." not in link:
        return fail("bad", 400)
    return create(body)


@app.route("/api/extra/posts/<int:post_id>/comments/", methods=["POST"])
def extra_comment(post_id):
    body = json.loads(request.data)
    if "tier1" in CHALLENGE and not all(isinstance(body.get(k), str) for k in ("text", "username")):
        return fail("bad", 400)
    return add_comment(post_id, body)


@app.route("/api/extra/posts/<int:post_id>/comments/<int:comment_id>/", methods=["POST"])
def extra_edit(post_id, comment_id):
    body = json.loads(request.data)
    if "tier1" in CHALLENGE and not isinstance(body.get("text"), str):
        return fail("bad", 400)
    return edit(post_id, comment_id, body)


@app.route("/api/extra/posts/<int:post_id>/", methods=["POST"])
def extra_upvote(post_id):
    if "upvote" not in CHALLENGE:
        return fail("not implemented", 501)
    body = json.loads(request.data if "no_default" in CHALLENGE else request.data or "{{}}")
    posts[post_id]["upvotes"] += body.get("upvotes", 1)
    return jsonify(serialize(posts[post_id]))


@app.route("/api/extra/posts/")
def extra_sorted():
    if "sort" not in CHALLENGE:
        return fail("not implemented", 501)
    reverse = request.args.get("sort") == "decreasing"
    ordered = sorted(posts.values(), key=lambda p: p["upvotes"], reverse=reverse)
    return jsonify({{"posts": [serialize(p) for p in ordered]}})
'''

ALL_CHALLENGE = {"tier1", "upvote", "sort"}


def pa1_app(broken=(), challenge=()):
    return PA1_APP.format(broken=set(broken), challenge=set(challenge))


# A PA2 app whose core and extra tests all pass.
PA2_APP = '''
import hashlib
import json
from flask import Flask, jsonify, request

app = Flask(__name__)
users = {}
next_id = [0]


def public(user):
    return {k: v for k, v in user.items() if k != "password"}


def hashed(password):
    return hashlib.sha256(str(password).encode()).hexdigest()


def create(keep_password):
    body = json.loads(request.data)
    if keep_password and body.get("password") is None:
        return jsonify({"error": "no password"}), 401
    next_id[0] += 1
    user = {"id": next_id[0], "name": body.get("name"), "username": body.get("username"),
            "balance": body.get("balance", 0)}
    if keep_password:
        user["password"] = hashed(body["password"])
    users[user["id"]] = user
    return jsonify(public(user)), 201


@app.route("/api/users/")
def get_users():
    return jsonify({"users": [public(u) for u in users.values()]})


@app.route("/api/users/", methods=["POST"])
def create_user():
    return create(False)


@app.route("/api/extra/users/", methods=["POST"])
def extra_create():
    return create(True)


@app.route("/api/user/<int:uid>/")
def get_user(uid):
    if uid not in users:
        return jsonify({"error": "nf"}), 404
    return jsonify(public(users[uid]))


@app.route("/api/extra/user/<int:uid>/", methods=["POST"])
def extra_get(uid):
    if users[uid].get("password") != hashed(json.loads(request.data).get("password")):
        return jsonify({"error": "no"}), 401
    return jsonify(public(users[uid]))


@app.route("/api/user/<int:uid>/", methods=["DELETE"])
def delete_user(uid):
    if uid not in users:
        return jsonify({"error": "nf"}), 404
    return jsonify(public(users.pop(uid)))


def send(check_password):
    body = json.loads(request.data)
    sender, receiver = users[body["sender_id"]], users[body["receiver_id"]]
    if check_password and sender.get("password") != hashed(body.get("password")):
        return jsonify({"error": "no"}), 401
    if sender["balance"] < body["amount"]:
        return jsonify({"error": "low"}), 400
    sender["balance"] -= body["amount"]
    receiver["balance"] += body["amount"]
    return jsonify({k: body[k] for k in ("sender_id", "receiver_id", "amount")})


@app.route("/api/send/", methods=["POST"])
def send_money():
    return send(False)


@app.route("/api/extra/send/", methods=["POST"])
def extra_send():
    return send(True)
'''
