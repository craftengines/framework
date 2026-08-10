{#
    Admin — CRUD builder result.

    Rendered by `app/Http/Controllers/Admin/CrudBuilderController.py::store`
    after a successful generation, behind `auth` + `role:admin`. Lists the files
    that were written and the routes that were registered, because a generator
    that reports only "done" leaves you guessing what changed.

    Context:
      entity        str    the generated entity name
      created       list   paths written
      show_sidebar  bool
#}
@extends("layouts.app")

@section("title", "CRUD Builder — Generated")

@section("content")
<div class="max-w-3xl bg-white border border-slate-200/80 rounded-3xl p-8 shadow-sm">
    <h1 class="text-2xl font-bold text-slate-900 mb-1">CRUD generated for {{ entity }}</h1>
    <p class="text-slate-500 text-sm mb-6">The files below were written to disk. Run pending migrations to create
        the table.</p>

    <div class="divide-y divide-slate-100 border border-slate-200 rounded-2xl overflow-hidden">
        @foreach(files.items() as kind, path)
            <div class="flex items-center justify-between px-5 py-3 text-sm">
                <span class="font-semibold text-slate-700">{{ kind.replace('_', ' ')|title }}</span>
                <code class="text-xs text-slate-500 font-mono">{{ path }}</code>
            </div>
        @endforeach
    </div>

    <div class="flex items-center space-x-4 pt-6">
        <a href="/admin/crud-builder"
           class="bg-orange-600 hover:bg-orange-700 text-white font-bold px-6 py-2.5 rounded-xl shadow-md transition duration-150 text-sm">
            Generate another
        </a>
        <a href="/admin" class="text-sm font-semibold text-slate-500 hover:text-slate-700">
            Back to dashboard
        </a>
    </div>
</div>
@endsection
