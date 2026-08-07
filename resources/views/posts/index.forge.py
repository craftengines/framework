@extends("layouts.app")

@section("title", "All Posts")

@section("content")
<div class="space-y-8">
    <!-- Header Area -->
    <div class="flex items-center justify-between">
        <div>
            <h1 class="text-3xl font-bold text-slate-900 tracking-tight">Posts & Discussions</h1>
            <p class="text-sm text-slate-500 mt-1">Read posts or write a new discussion thread</p>
        </div>
        @auth
            <a href="/posts/create" class="bg-orange-600 hover:bg-orange-700 text-white font-bold px-5 py-2.5 rounded-xl shadow-md transition duration-150 text-sm">
                New Post
            </a>
        @endauth
    </div>

    <!-- Posts Grid -->
    @if(posts is defined and posts is not none and 'data' in posts and posts['data']|length > 0)
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            @foreach(posts['data'] as post)
                <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:border-orange-200 hover:shadow-md transition flex flex-col justify-between h-64">
                    <div>
                        <div class="flex items-center justify-between text-[10px] text-slate-400 font-mono mb-3">
                            <span class="bg-orange-50 text-orange-600 font-bold px-2 py-0.5 rounded">DISCUSSION</span>
                            <span>{{ post.get('created_at') }}</span>
                        </div>
                        <h2 class="text-lg font-bold text-slate-800 hover:text-orange-600 transition line-clamp-2">
                            <a href="/posts/{{ post.get('id') }}">
                                {{ post.get('title') }}
                            </a>
                        </h2>
                        <p class="text-slate-500 text-sm leading-relaxed line-clamp-3 mt-3">
                            {{ post.get('body') }}
                        </p>
                    </div>
                    
                    <div class="border-t border-slate-100 pt-4 flex items-center justify-between text-xs">
                        <span class="text-slate-400">Author: System User</span>
                        <a href="/posts/{{ post.get('id') }}/edit" class="text-orange-600 hover:text-orange-700 font-semibold">
                            Edit Post &rarr;
                        </a>
                    </div>
                </div>
            @endforeach
        </div>
    @else
        <div class="text-center py-16 bg-white border border-dashed border-slate-200 rounded-3xl text-slate-400 max-w-lg mx-auto">
            <svg class="w-12 h-12 text-slate-300 mx-auto mb-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 7.5h1.5m-1.5 3h1.5m-7.5 3h7.5m-7.5 3h7.5m3-9h3.375c.621 0 1.125.504 1.125 1.125V18a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 18V6A2.25 2.25 0 015.25 3.75h9L18 7.5zm-3 0h.008v.008H15V7.5z"></path>
            </svg>
            <p class="text-sm font-semibold">No discussions posted yet.</p>
            @auth
                <p class="text-xs text-slate-400 mt-1 mb-4">Be the first to create one!</p>
                <a href="/posts/create" class="bg-orange-600 hover:bg-orange-700 text-white font-bold px-4 py-2 rounded-xl shadow-md transition duration-150 text-xs">
                    Create a Post
                </a>
            @endauth
        </div>
    @endif
</div>
@endsection
