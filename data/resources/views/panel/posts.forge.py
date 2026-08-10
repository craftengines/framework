{#
    Panel — Posts.

    Rendered by `app/Http/Controllers/Panel/PanelController.py::posts` at
    `GET /panel/posts`, behind `auth`.

    One template, two audiences: an ordinary account sees only its own posts
    (the controller narrows the query by `user_id`), an administrator sees
    every post and gains an Author column. Scoping in the query rather than in
    the template means a rendering mistake cannot leak someone else's rows.

    Context:
      posts     list[Post]
      is_admin  bool   drives the extra column, not the visibility
#}
@extends("layouts.panel")

@section("title", "Posts")

@section("actions")
    @can("create-post")
        <a href="/posts/create" class="bg-orange-600 hover:bg-orange-700 text-white text-sm font-bold px-5 py-2.5 rounded-xl shadow-sm transition">
            New post
        </a>
    @endcan
@endsection

@section("content")

<div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
    @if(posts|length > 0)
        <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-slate-50/75 border-b border-slate-200 text-[10px] font-bold uppercase text-slate-500 font-mono">
                        <th class="px-5 py-3">Title</th>
                        @if(is_admin)
                            <th class="px-5 py-3">Author</th>
                        @endif
                        <th class="px-5 py-3">Created</th>
                        <th class="px-5 py-3 text-right">Actions</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-sm">
                    @foreach(posts as post)
                        <tr class="hover:bg-slate-50/50">
                            <td class="px-5 py-3.5">
                                <a href="/posts/{{ post.get_attribute('id') }}" class="font-semibold text-slate-900 hover:text-orange-600">
                                    {{ post.get_attribute('title') }}
                                </a>
                            </td>
                            @if(is_admin)
                                <td class="px-5 py-3.5 font-mono text-xs text-slate-500">#{{ post.get_attribute('user_id') }}</td>
                            @endif
                            <td class="px-5 py-3.5 font-mono text-xs text-slate-400">{{ post.get_attribute('created_at') }}</td>
                            <td class="px-5 py-3.5 text-right">
                                <a href="/posts/{{ post.get_attribute('id') }}/edit" class="text-xs font-semibold text-slate-500 hover:text-orange-600">Edit</a>
                            </td>
                        </tr>
                    @endforeach
                </tbody>
            </table>
        </div>
    @else
        <div class="px-5 py-16 text-center">
            <p class="text-sm font-semibold text-slate-900">Nothing here yet.</p>
            <p class="text-xs text-slate-500 mt-1 mb-4">Posts you write will be listed here.</p>
            @can("create-post")
                <a href="/posts/create" class="inline-block bg-orange-600 hover:bg-orange-700 text-white text-sm font-bold px-5 py-2.5 rounded-xl shadow-sm transition">
                    Write a post
                </a>
            @endcan
        </div>
    @endif
</div>

@endsection
