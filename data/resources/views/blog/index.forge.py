{# Blog Feed Template #}
@extends("layouts.app")

@section("title", "Blog & Articles — Craft Engine")

@section("content")
    <div class="max-w-4xl mx-auto space-y-8">
        <div class="border-b border-slate-200 pb-6">
            <h1 class="text-3xl font-extrabold text-slate-900 tracking-tight">Craft Engine Blog</h1>
            <p class="text-slate-600 mt-2">Latest news, articles and technical tutorials.</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            @for post in posts
                <article class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition">
                    <h2 class="text-xl font-bold text-slate-900 mb-2">
                        <a href="/blog/{{ post.get_attribute('slug') }}" class="hover:text-indigo-600">
                            {{ post.get_attribute('title') }}
                        </a>
                    </h2>
                    <p class="text-slate-600 text-sm mb-4 line-clamp-3">
                        {{ post.get_attribute('excerpt') or post.get_attribute('content') }}
                    </p>
                    <div class="flex items-center justify-between text-xs text-slate-400 font-mono">
                        <span>{{ post.get_attribute('published_at') or post.get_attribute('created_at') }}</span>
                        <a href="/blog/{{ post.get_attribute('slug') }}" class="text-indigo-600 font-semibold hover:underline">Read &rarr;</a>
                    </div>
                </article>
            @endfor
        </div>
    </div>
@endsection
