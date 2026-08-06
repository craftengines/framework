@extends("layouts.app")

@section("title", post.get_attribute('title'))

@section("content")
    <div class="post">
        <h1>{{ post.get_attribute('title') }}</h1>
        <div class="meta">Published on {{ post.get_attribute('created_at') }}</div>
        <div class="body">{{ post.get_attribute('body') }}</div>
    </div>
    <a href="/posts" class="btn">&larr; Back to Posts</a>
@endsection
