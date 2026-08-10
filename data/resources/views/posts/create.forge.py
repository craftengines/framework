{#
    Blog — new post form.

    Rendered by `app/Http/Controllers/Blog/PostController.py::create`, and
    re-rendered by `store()` when validation fails, so errors and the submitted
    values survive. Requires a logged-in session.

    Context:
      errors        dict  validation messages, keyed by field ({} on first load)
      show_sidebar  bool
#}
@extends("layouts.app")

@section("title", "Create Post")

@section("content")
<div class="max-w-2xl bg-white border border-slate-200/80 rounded-3xl p-8 shadow-sm">
    <h1 class="text-2xl font-bold text-slate-900 mb-6">Create New Post</h1>

    @if(errors|length > 0)
    <div class="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-100 text-rose-700 text-sm space-y-1">
        @foreach(errors.values() as messages)
            @foreach(messages as message)
                <p>{{ message }}</p>
            @endforeach
        @endforeach
    </div>
    @endif

    <form action="/posts" method="POST" class="space-y-6">
        @csrf

        <div class="space-y-2">
            <label for="title" class="block text-sm font-semibold text-slate-700">Title</label>
            <input type="text" name="title" id="title" value="{{ old('title') }}" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500" required>
        </div>

        <div class="space-y-2">
            <label for="body" class="block text-sm font-semibold text-slate-700">Content Body</label>
            <textarea name="body" id="body" rows="6" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500" required>{{ old('body') }}</textarea>
        </div>

        <div class="flex items-center">
            <input type="checkbox" name="published" id="published" value="1" {% if old('published') %}checked{% endif %} class="h-4 w-4 text-orange-600 focus:ring-orange-500 border-slate-300 rounded">
            <label for="published" class="ml-2 block text-sm text-slate-700 font-medium">Publish immediately</label>
        </div>
        
        <div class="flex items-center space-x-4 pt-2">
            <button type="submit" class="bg-orange-600 hover:bg-orange-700 text-white font-bold px-6 py-2.5 rounded-xl shadow-md transition duration-150 text-sm">
                Create Post
            </button>
            <a href="/posts" class="text-sm font-semibold text-slate-500 hover:text-slate-700">
                Cancel
            </a>
        </div>
    </form>
</div>
@endsection
