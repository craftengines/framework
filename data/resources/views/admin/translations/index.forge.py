@extends("layouts.app")

@section("title", "Traduções")

@section("content")
<div class="space-y-6">
    <div>
        <h1 class="text-2xl font-bold text-slate-900">Gerenciador de Traduções</h1>
        <p class="text-sm text-slate-500">Gestão e edição de dicionários do sistema</p>
    </div>

    <div class="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <table class="w-full text-left text-sm text-slate-600">
            <thead class="bg-slate-50 border-b border-slate-200 text-xs uppercase font-semibold text-slate-500">
                <tr>
                    <th class="px-6 py-3">Grupo</th>
                    <th class="px-6 py-3">Chave</th>
                    <th class="px-6 py-3">Idioma</th>
                    <th class="px-6 py-3">Valor</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
                @if(translations is defined and translations|length > 0)
                    @foreach(translations as t)
                        <tr class="hover:bg-slate-50 transition">
                            <td class="px-6 py-4 font-mono text-xs">{{ t.get_attribute('group') }}</td>
                            <td class="px-6 py-4 font-mono text-xs">{{ t.get_attribute('key') }}</td>
                            <td class="px-6 py-4"><span class="bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-xs">{{ t.get_attribute('locale') }}</span></td>
                            <td class="px-6 py-4 text-slate-900">{{ t.get_attribute('value') }}</td>
                        </tr>
                    @endforeach
                @else
                    <tr>
                        <td colspan="4" class="px-6 py-12 text-center text-slate-400">Nenhuma tradução encontrada.</td>
                    </tr>
                @endif
            </tbody>
        </table>
    </div>
</div>
@endsection
