"""Post controller — demonstrates CRUD with models, validation, and resources under Blog directory."""

from codepy.http.controller import Controller
from codepy.http.response import JsonResponse, Response, redirect
from app.Models.Post import Post
from app.Http.Requests.StorePostRequest import StorePostRequest
from app.Http.Resources.PostResource import PostResource


class PostController(Controller):
    def index(self, request):
        posts = Post.query().order_by_desc("created_at").paginate(15)
        if request.expects_json():
            # Convert each post to a resource dict for JSON serialization
            return JsonResponse([PostResource(p).to_array() for p in posts])
        return self.view("posts.index", {"posts": posts})

    def create(self, request):
        return self.view("posts.create", {"show_sidebar": True})

    def store(self, request):
        from codepy.facades import Auth
        form = StorePostRequest(request)
        data = form.validated()
        
        user = Auth.user()
        data["user_id"] = user.get_attribute("id") if user else 1
        
        post = Post.create(data)
        if request.expects_json():
            return PostResource(post).response(status=201)
        return redirect(route="posts.index")

    def show(self, request, posts):
        post = Post.query().where("id", posts).first()
        if not post:
            return Response("Not found", 404)
        if request.expects_json():
            return PostResource(post)
        return self.view("posts.show", {"post": post})

    def edit(self, request, posts):
        post = Post.query().where("id", posts).first()
        return self.view("posts.edit", {"post": post, "show_sidebar": True})

    def update(self, request, posts):
        post = Post.query().where("id", posts).first()
        form = StorePostRequest(request)
        post.update_attributes(form.validated())
        if request.expects_json():
            return PostResource(post)
        return redirect(route="posts.index")

    def destroy(self, request, posts):
        post = Post.query().where("id", posts).first()
        if post:
            post.delete()
        if request.expects_json():
            return self.no_content()
        return redirect(route="posts.index")
