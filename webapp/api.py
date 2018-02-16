import json
import flask
import logging
from datetime import datetime, timezone, timedelta
from schema import ScopedSession, SyncState, User, Post, Comment

DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


app = flask.Flask(__name__)

def parse_date(date):
    return datetime.strptime(date, DATE_FORMAT)

@app.route('/state')
def state():
    with ScopedSession() as session:
        pending = session.query(SyncState.post_id).filter_by(pending=True).count()
        total = session.query(SyncState.post_id).count()

    return flask.jsonify({
        "pending": pending,
        "total": total
    })


@app.route('/comments')
def comments():
    with ScopedSession() as session:
        query = session.query(Comment, User).filter(Comment.user_id == User.user_id)

        before = flask.request.args.get('before')
        if before is not None:
            query = query.filter(Comment.posted < parse_date(before))

        ignore = flask.request.args.get('ignore')
        if ignore:
            ignore = [int(u) for u in ignore.split(',')]
            query = query.filter(Comment.user_id.notin_(ignore))

        comments = []

        for comment, user in query.order_by(Comment.posted.desc()).limit(20).all():
            comments.append({
                "id": comment.comment_id,
                "parent_id": comment.parent_id,
                "post_id": comment.post_id,
                "text": comment.text,
                "posted": comment.posted.strftime(DATE_FORMAT),
                "user_id": user.user_id,
                "user_name": user.name,
                "user_avatar": user.avatar_hash
            })

    resp = app.make_response(json.dumps(comments, ensure_ascii=False))
    resp.mimetype = 'application/json; charset=utf-8'

    return resp

@app.route('/post/<post_id>')
def post(post_id):
    post_id = int(post_id)

    with ScopedSession() as session:
        post = session.query(Post).get(post_id)
        user = session.query(User).get(post.user_id)

        resp = {
            "id": post.post_id,
            "code": post.code,
            "text": post.text,
            "posted": post.posted.strftime(DATE_FORMAT),
            "user_id": user.user_id,
            "user_name": user.name,
            "user_avatar": user.avatar_hash
        }

        comments = []
        for comment, user in session.query(Comment, User).filter(Comment.post_id == post_id).filter(Comment.user_id == User.user_id).order_by(Comment.posted.asc()).all():
            comments.append({
                "id": comment.comment_id,
                "parent_id": comment.parent_id,
                "text": comment.text,
                "posted": comment.posted.strftime(DATE_FORMAT),
                "user_id": user.user_id,
                "user_name": user.name,
                "user_avatar": user.avatar_hash
            })
        resp["comments"] = comments

        resp = app.make_response(json.dumps(resp, ensure_ascii=False))
        resp.mimetype = 'application/json; charset=utf-8'

        return resp