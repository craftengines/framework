{# Blog Post View Template #}
@extends("layouts.app")

@section("title", post.get_attribute('title'))

@section("content")
    <article class="max-w-3xl mx-auto bg-white p-8 rounded-3xl border border-slate-200 shadow-sm space-y-6">
        <header class="space-y-3">
            <h1 class="text-3xl font-extrabold text-slate-900 leading-tight">{{ post.get_attribute('title') }}</h1>
            <div class="text-xs text-slate-400 font-mono">
                Published on {{ post.get_attribute('published_at') or post.get_attribute('created_at') }}
            </div>
        </header>

        <div class="prose prose-slate text-slate-700 leading-relaxed whitespace-pre-line">
            {{ post.get_attribute('content') }}
        </div>

        <hr class="border-slate-200 my-8" />

        <section class="space-y-6">
            <h3 class="text-xl font-bold text-slate-900">Comments</h3>
            <div class="space-y-4">
                @for comment in comments
                    <div class="bg-slate-50 p-4 rounded-xl border border-slate-100">
                        <div class="font-semibold text-slate-800 text-sm mb-1">{{ comment.get_attribute('author_name') }}</div>
                        <div class="text-slate-600 text-sm">{{ comment.get_attribute('content') }}</div>
                    </div>
                @endfor
            </div>

            <form method="POST" action="/blog/{{ post.get_attribute('slug') }}/comments" class="space-y-4 bg-slate-50 p-6 rounded-2xl border border-slate-200">
                <h4 class="font-bold text-slate-800">Leave a comment</h4>
                <div>
                    <label class="block text-xs font-semibold text-slate-600 mb-1">Your Name</label>
                    <input type="text" name="author_name" required class="w-full px-3 py-2 text-sm border rounded-lg" />
                </div>
                <div>
                    <label class="block text-xs font-semibold text-slate-600 mb-1">Comment</label>
                    <textarea name="content" rows="3" required class="w-full px-3 py-2 text-sm border rounded-lg"></textarea>
                </div>
                <button type="submit" class="px-4 py-2 bg-indigo-600 text-white font-semibold text-sm rounded-lg hover:bg-indigo-700">Submit Comment</button>
            </form>
        </section>
    </article>
@endsection
