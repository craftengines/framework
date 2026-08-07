@extends("layouts.app")

@section("title", "CRUD Builder — Admin")

@section("content")
<div class="max-w-4xl bg-white border border-slate-200/80 rounded-3xl p-8 shadow-sm">
    <h1 class="text-2xl font-bold text-slate-900 mb-1">CRUD Builder</h1>
    <p class="text-slate-500 text-sm mb-6">Describe an entity and its fields; a migration, model, controller,
        form request, resource and route are generated for you.</p>

    @if(errors|length > 0)
    <div class="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-100 text-rose-700 text-sm space-y-1">
        @foreach(errors as message)
            <p>{{ message }}</p>
        @endforeach
    </div>
    @endif

    <form action="/admin/crud-builder" method="POST" class="space-y-6" id="crud-builder-form">
        @csrf

        <div class="space-y-2">
            <label for="entity" class="block text-sm font-semibold text-slate-700">Entity name</label>
            <input type="text" name="entity" id="entity" value="{{ entity }}" placeholder="Product"
                   class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500"
                   required>
            <p class="text-xs text-slate-400">Singular, PascalCase or snake_case — e.g. "Product" or "order_item".</p>
        </div>

        <div class="space-y-2">
            <div class="flex items-center justify-between">
                <label class="block text-sm font-semibold text-slate-700">Fields</label>
                <button type="button" id="add-field-row"
                        class="text-xs font-bold text-orange-600 hover:text-orange-700">+ Add field</button>
            </div>

            <div id="field-rows" class="space-y-3"></div>
        </div>

        <div class="flex items-center space-x-4 pt-2">
            <button type="submit"
                    class="bg-orange-600 hover:bg-orange-700 text-white font-bold px-6 py-2.5 rounded-xl shadow-md transition duration-150 text-sm">
                Generate CRUD
            </button>
        </div>
    </form>
</div>

<template id="field-row-template">
    <div class="flex items-center space-x-3 field-row">
        <input type="text" placeholder="name" class="flex-1 px-3 py-2 rounded-lg border border-slate-200 text-sm field-name-input">
        <select class="px-3 py-2 rounded-lg border border-slate-200 text-sm field-type-input">
            @foreach(field_types as type)
                <option value="{{ type }}">{{ type }}</option>
            @endforeach
        </select>
        <label class="flex items-center text-xs text-slate-500 space-x-1">
            <input type="checkbox" class="field-required-input">
            <span>required</span>
        </label>
        <button type="button" class="text-xs text-rose-500 hover:text-rose-600 remove-field-row">Remove</button>
    </div>
</template>

<script>
(function () {
    var rowsContainer = document.getElementById("field-rows");
    var template = document.getElementById("field-row-template");
    var form = document.getElementById("crud-builder-form");
    var counter = 0;

    function addRow() {
        var index = counter++;
        var fragment = template.content.cloneNode(true);
        var row = fragment.querySelector(".field-row");

        var nameInput = row.querySelector(".field-name-input");
        nameInput.name = "field_name_" + index;

        var typeInput = row.querySelector(".field-type-input");
        typeInput.name = "field_type_" + index;

        var requiredInput = row.querySelector(".field-required-input");
        requiredInput.name = "field_required_" + index;

        row.querySelector(".remove-field-row").addEventListener("click", function () {
            row.remove();
        });

        rowsContainer.appendChild(row);
    }

    document.getElementById("add-field-row").addEventListener("click", addRow);
    form.addEventListener("submit", function () {
        // Checkboxes only submit when checked — nothing else to normalise here.
    });

    addRow();
})();
</script>
@endsection
