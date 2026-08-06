@extends("layouts.app")

@section("title", "Acesso a Arquivos")

@section("content")
<div class="space-y-6">
    <div>
        <h1 class="text-2xl font-bold text-slate-900">🔐 Controle de Acesso a Arquivos e Impressão</h1>
        <p class="text-sm text-slate-500">Defina, por papel, quem pode ver e imprimir cada categoria</p>
    </div>

    <form method="POST" action="/access/save" class="space-y-4">
        <div class="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            <table class="w-full text-left text-sm text-slate-600">
                <thead class="bg-slate-50 border-b border-slate-200 text-xs uppercase font-semibold text-slate-500">
                    <tr>
                        <th class="px-6 py-3">Papel</th>
                        <th class="px-6 py-3 text-center">Ações</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                    @if(roles is defined and roles|length > 0)
                        @foreach(roles as rk, rl)
                            <tr class="hover:bg-slate-50 transition">
                                <td class="px-6 py-4 font-medium text-slate-900">{{ rl }}</td>
                                <td class="px-6 py-4 text-center space-x-4">
                                    <label class="inline-flex items-center text-xs">
                                        <input type="checkbox" name="p[{{ rk }}][view]" value="1" class="rounded border-slate-300 text-indigo-600 mr-1"> Ver
                                    </label>
                                    <label class="inline-flex items-center text-xs">
                                        <input type="checkbox" name="p[{{ rk }}][print]" value="1" class="rounded border-slate-300 text-indigo-600 mr-1"> Imprimir
                                    </label>
                                </td>
                            </tr>
                        @endforeach
                    @endif
                </tbody>
            </table>
        </div>
        <div>
            <button type="submit" class="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-4 py-2 rounded-lg text-sm transition">
                Salvar Política de Acesso
            </button>
        </div>
    </form>
</div>
@endsection
