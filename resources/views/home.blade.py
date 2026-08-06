@extends("layouts.app")

@section("title", "Codepy — " ~ __('small_framework_title'))

@section("content")
    <!-- CodeIgniter-style Hero Section -->
    <div class="py-12 md:py-20 text-center max-w-4xl mx-auto space-y-6">
        <!-- Title -->
        <h1 class="text-6xl md:text-7xl font-light text-orange-600 tracking-tight font-sans">
            Codepy <sup class="text-2xl md:text-3xl font-light text-orange-600">{{ config('app.version') }}</sup>
        </h1>

        <!-- Subtitle -->
        <p class="text-2xl md:text-3xl text-slate-700 font-light tracking-wide">
            {{ __('small_framework_title') }}
        </p>

        <!-- Paragraph Description -->
        <p class="text-sm md:text-base text-slate-500 max-w-3xl mx-auto leading-relaxed">
            {{ __('framework_description') }}
        </p>

        <!-- Learn More Button -->
        <div class="pt-4">
            <a href="/docs" class="bg-orange-600 hover:bg-orange-700 text-white font-medium px-8 py-3 rounded-lg text-sm transition shadow-sm inline-block">
                {{ __('learn_more') }}
            </a>
        </div>

        <!-- Git Badges style -->
        <div class="flex items-center justify-center space-x-6 pt-4 text-xs text-slate-600">
            <a href="https://github.com" target="_blank" class="flex items-center space-x-1.5 hover:text-orange-600 transition">
                <svg class="w-4 h-4 text-slate-900" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2A10 10 0 002 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.9-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.9 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0012 2z"></path></svg>
                <span class="font-semibold">Star</span>
                <span class="bg-slate-100 border border-slate-200 px-2 py-0.5 rounded text-[10px] font-bold">5,955</span>
            </a>
            <a href="https://github.com" target="_blank" class="flex items-center space-x-1.5 hover:text-orange-600 transition">
                <svg class="w-3.5 h-3.5 text-slate-950" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 15L12 18.75 15.75 15m-7.5-6L12 5.25 15.75 9"></path></svg>
                <span class="font-semibold">Fork</span>
                <span class="bg-slate-100 border border-slate-200 px-2 py-0.5 rounded text-[10px] font-bold">1,995</span>
            </a>
        </div>
    </div>

    <!-- Why Codepy section -->
    <div class="py-12 border-t border-slate-100 max-w-5xl mx-auto">
        <h2 class="text-3xl font-normal text-orange-600 text-center mb-16 font-sans">
            {{ __('why_codepy') }}
        </h2>

        <!-- Feature Grid (2 columns, 2 rows) -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-10">
            <!-- Feature 1 -->
            <div class="flex items-start space-x-4">
                <div class="w-10 h-10 flex-shrink-0 text-orange-600 border border-orange-200 rounded-lg flex items-center justify-center">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M11.48 3.499c-.107-.183-.3-.299-.512-.299s-.405.116-.512.299L4.99 12.302c-.104.178-.108.397-.01.579.098.182.288.297.494.297h4.086v5.822c0 .408.33.738.738.738h1.404a.738.738 0 00.738-.738V13.48h4.086c.206 0 .396-.115.494-.297.098-.182.094-.401-.01-.579l-5.467-8.804z"></path></svg>
                </div>
                <div class="space-y-1">
                    <h3 class="text-base font-bold text-slate-800">{{ __('small_footprint_title') }}</h3>
                    <p class="text-slate-500 text-sm leading-relaxed">
                        {{ __('small_footprint_desc') }}
                    </p>
                </div>
            </div>

            <!-- Feature 2 -->
            <div class="flex items-start space-x-4">
                <div class="w-10 h-10 flex-shrink-0 text-orange-600 border border-orange-200 rounded-lg flex items-center justify-center">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"></path></svg>
                </div>
                <div class="space-y-1">
                    <h3 class="text-base font-bold text-slate-800">{{ __('exceptional_perf_title') }}</h3>
                    <p class="text-slate-500 text-sm leading-relaxed">
                        {{ __('exceptional_perf_desc') }}
                    </p>
                </div>
            </div>

            <!-- Feature 3 -->
            <div class="flex items-start space-x-4">
                <div class="w-10 h-10 flex-shrink-0 text-orange-600 border border-orange-200 rounded-lg flex items-center justify-center">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L6 12zm0 0h7.5"></path></svg>
                </div>
                <div class="space-y-1">
                    <h3 class="text-base font-bold text-slate-800">{{ __('simple_solutions_title') }}</h3>
                    <p class="text-slate-500 text-sm leading-relaxed">
                        {{ __('simple_solutions_desc') }}
                    </p>
                </div>
            </div>

            <!-- Feature 4 -->
            <div class="flex items-start space-x-4">
                <div class="w-10 h-10 flex-shrink-0 text-orange-600 border border-orange-200 rounded-lg flex items-center justify-center">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.57-.598-3.751h-.152c-3.196 0-6.1-1.249-8.25-3.286z"></path></svg>
                </div>
                <div class="space-y-1">
                    <h3 class="text-base font-bold text-slate-800">{{ __('strong_security_title') }}</h3>
                    <p class="text-slate-500 text-sm leading-relaxed">
                        {{ __('strong_security_desc') }}
                    </p>
                </div>
            </div>
        </div>
    </div>

    <!-- Recent Posts Section (Forum / Discussions) -->
    <div class="py-12 border-t border-slate-100 max-w-5xl mx-auto">
        <div class="flex items-center justify-between mb-8">
            <h3 class="text-xl font-bold text-slate-800 font-sans">{{ __('recent_posts') }}</h3>
            <a href="/posts" class="text-sm font-semibold text-orange-600 hover:text-orange-700">{{ __('discuss') }} &rarr;</a>
        </div>

        @if(posts is defined and posts is not none and posts|length > 0)
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                @foreach(posts as post)
                    <div class="bg-white p-6 rounded-xl border border-slate-200/60 shadow-[0_1px_3px_rgba(0,0,0,0.02)] hover:border-orange-200 transition">
                        <span class="text-[10px] text-orange-600 font-bold uppercase tracking-wider block mb-1">Forum Topic</span>
                        <h4 class="text-base font-bold text-slate-800 hover:text-orange-600 transition mb-2">
                            <a href="{{ route('posts.show', post=post.get_attribute('id')) }}">
                                {{ post.get_attribute('title') }}
                            </a>
                        </h4>
                        <p class="text-slate-500 text-xs leading-relaxed line-clamp-2 mb-4">
                            {{ post.get_attribute('body') }}
                        </p>
                        <div class="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                            <span>Author: System Manager</span>
                            <span>{{ post.get_attribute('created_at') }}</span>
                        </div>
                    </div>
                @endforeach
            </div>
        @else
            <div class="text-center py-8 border border-dashed border-slate-200 rounded-xl text-slate-400 text-sm">
                No active forum discussions posted.
            </div>
        @endif
    </div>
@endsection
