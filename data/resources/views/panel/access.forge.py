{#
    Panel — My access.

    Rendered by `app/Http/Controllers/Panel/PanelController.py::access` at
    `GET /panel/access`, behind `auth`. Shows the visitor their own roles,
    groups and permissions — never anyone else's.

    The grant table is the interesting part: it names the *path* each
    permission arrives by and the conditions attached to it, straight from the
    same resolver that makes the decision. "Why can I do this?" is a question
    both users and auditors ask, and answering it from a second source is how
    the screen ends up disagreeing with the enforcement.

    Context:
      roles   list[str]
      groups  list[str]
      grants  list[{slug, source, conditions}]
#}
@extends("layouts.panel")

@section("title", "My access")

@section("content")

<div class="grid gap-4 sm:grid-cols-2">
    <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
        <p class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">Roles</p>
        @if(roles|length > 0)
            <div class="flex flex-wrap gap-1.5">
                @foreach(roles as role)
                    <span class="inline-flex px-2.5 py-1 rounded-lg text-xs font-semibold bg-orange-50 text-orange-700 font-mono">{{ role }}</span>
                @endforeach
            </div>
        @else
            <p class="text-sm text-slate-400">No roles assigned.</p>
        @endif
    </div>

    <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
        <p class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">Groups</p>
        @if(groups|length > 0)
            <div class="flex flex-wrap gap-1.5">
                @foreach(groups as group)
                    <span class="inline-flex px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-100 text-slate-700 font-mono">{{ group }}</span>
                @endforeach
            </div>
        @else
            <p class="text-sm text-slate-400">Not a member of any group.</p>
        @endif
    </div>
</div>

<div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
    <div class="px-5 py-4 border-b border-slate-100">
        <h3 class="text-sm font-bold text-slate-900">Permissions</h3>
        <p class="text-xs text-slate-500 mt-0.5">
            One row per grant. The same permission can arrive by more than one path.
        </p>
    </div>

    @if(grants|length > 0)
        <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-slate-50/75 border-b border-slate-200 text-[10px] font-bold uppercase text-slate-500 font-mono">
                        <th class="px-5 py-3">Permission</th>
                        <th class="px-5 py-3">Granted via</th>
                        <th class="px-5 py-3">Conditions</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-sm">
                    @foreach(grants as grant)
                        <tr>
                            <td class="px-5 py-3 font-mono text-xs font-semibold text-slate-900">{{ grant['slug'] }}</td>
                            <td class="px-5 py-3">
                                <span class="inline-flex px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-600 font-mono">{{ grant['source'] }}</span>
                            </td>
                            <td class="px-5 py-3">
                                {# A conditional grant is not the same permission as an
                                   unconditional one. Showing the condition verbatim is
                                   the difference between "you may publish" and "you may
                                   publish your own drafts". #}
                                @if(grant['conditions'])
                                    <code class="text-[11px] text-slate-600 bg-slate-50 px-2 py-1 rounded">{{ grant['conditions'] }}</code>
                                @else
                                    <span class="text-[11px] text-slate-400">unconditional</span>
                                @endif
                            </td>
                        </tr>
                    @endforeach
                </tbody>
            </table>
        </div>
    @else
        <div class="px-5 py-12 text-center">
            <p class="text-sm font-semibold text-slate-900">No permissions granted.</p>
            <p class="text-xs text-slate-500 mt-1">An administrator can add your account to a group or assign it a role.</p>
        </div>
    @endif
</div>

@endsection
