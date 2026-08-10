{#
    Blog — a single post.

    Rendered by `app/Http/Controllers/Blog/PostController.py::show` at
    `GET /posts/{id}`. Public. A missing id returns 404 from the controller
    rather than rendering an empty page.

    Context:
      post   Post
#}
@extends("layouts.app")

@section("title", post.get_attribute('title'))

@section("content")
    <div class="max-w-2xl bg-white border border-slate-200/80 rounded-3xl p-8 shadow-sm space-y-4">
        <h1 class="text-2xl font-bold text-slate-900">{{ post.get_attribute('title') }}</h1>
        <div class="text-xs text-slate-400 font-mono">Published on {{ post.get_attribute('created_at') }}</div>
        <div class="text-slate-700 leading-relaxed whitespace-pre-line">{{ post.get_attribute('body') }}</div>
    </div>
    <a href="/posts" class="inline-block mt-6 text-sm font-semibold text-slate-500 hover:text-slate-700">&larr; Back to Posts</a>
@endsection
