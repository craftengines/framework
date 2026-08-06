@extends("layouts.app")

@section("title", "Edit Post")

@section("content")
<div class="max-w-2xl bg-white border border-slate-200/80 rounded-3xl p-8 shadow-sm">
    <h1 class="text-2xl font-bold text-slate-900 mb-6">Edit Post</h1>
    
    <form action="/posts/{{ post.get_attribute('id') }}" method="POST" class="space-y-6">
        @csrf
        <input type="hidden" name="_method" value="PUT">
        
        <div class="space-y-2">
            <label for="title" class="block text-sm font-semibold text-slate-700">Title</label>
            <input type="text" name="title" id="title" value="{{ post.get_attribute('title') }}" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500" required>
        </div>
        
        <div class="space-y-2">
            <label for="body" class="block text-sm font-semibold text-slate-700">Content Body</label>
            <textarea name="body" id="body" rows="6" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500" required>{{ post.get_attribute('body') }}</textarea>
        </div>
        
        <div class="flex items-center">
            <input type="checkbox" name="published" id="published" value="1" {% if post.get_attribute('published') %}checked{% endif %} class="h-4 w-4 text-orange-600 focus:ring-orange-500 border-slate-300 rounded">
            <label for="published" class="ml-2 block text-sm text-slate-700 font-medium">Published</label>
        </div>
        
        <div class="flex items-center space-x-4 pt-2">
            <button type="submit" class="bg-orange-600 hover:bg-orange-700 text-white font-bold px-6 py-2.5 rounded-xl shadow-md transition duration-150 text-sm">
                Update Post
            </button>
            <a href="/posts" class="text-sm font-semibold text-slate-500 hover:text-slate-700">
                Cancel
            </a>
        </div>
    </form>
</div>
@endsection
