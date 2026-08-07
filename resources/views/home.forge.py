@extends("layouts.app")

@section("title", "Craft — The Python Framework for Expressive Web Applications")

@section("content")
    <!-- Hero Section -->
    <div class="hero-section">
        <div class="hero-glow"></div>
        <div class="hero-content">
            <div class="hero-badge">
                <span class="badge-dot"></span>
                <span>Open Source · MIT License</span>
            </div>
            <h1 class="hero-title">
                Craft <sup class="hero-version">{{ config('app.version') }}</sup>
            </h1>
            <p class="hero-subtitle">
                The Python Framework for Expressive Web Applications
            </p>
            <p class="hero-description">
                Build powerful web applications in Python with conventions that stay out of your way.
                Craft ORM, Forge templates, migrations and auth — batteries included.
            </p>
            <div class="hero-actions">
                <a href="/docs/installation" class="btn-primary" id="hero-learn-more">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>
                    Read the Docs
                </a>
                <a href="#quickstart" class="btn-secondary" id="hero-quickstart">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>
                    {{ __('learn_more') }}
                </a>
            </div>
            <div class="hero-stats">
                <div class="stat-item">
                    <span class="stat-value">530</span>
                    <span class="stat-label">Tests Passing</span>
                </div>
                <div class="stat-divider"></div>
                <div class="stat-item">
                    <span class="stat-value">3</span>
                    <span class="stat-label">DB Drivers</span>
                </div>
                <div class="stat-divider"></div>
                <div class="stat-item">
                    <span class="stat-value">MIT</span>
                    <span class="stat-label">License</span>
                </div>
                <div class="stat-divider"></div>
                <div class="stat-item">
                    <span class="stat-value">Py 3.11+</span>
                    <span class="stat-label">Runtime</span>
                </div>
            </div>
        </div>

        <!-- Animated Code Preview -->
        <div class="hero-code-card">
            <div class="code-card-header">
                <div class="code-dots">
                    <span class="dot dot-red"></span>
                    <span class="dot dot-yellow"></span>
                    <span class="dot dot-green"></span>
                </div>
                <span class="code-filename">app/Http/Controllers/PostController.py</span>
            </div>
            <pre class="code-block"><code><span class="code-keyword">from</span> <span class="code-module">craft.facades</span> <span class="code-keyword">import</span> Route, Auth
<span class="code-keyword">from</span> <span class="code-module">craft.orm.model</span> <span class="code-keyword">import</span> Model

<span class="code-keyword">class</span> <span class="code-class">Post</span>(Model):
    __table__ = <span class="code-string">"posts"</span>
    fillable = [<span class="code-string">"title"</span>, <span class="code-string">"body"</span>]

    <span class="code-keyword">def</span> <span class="code-func">author</span>(self):
        <span class="code-keyword">return</span> self.belongs_to(User)

<span class="code-comment"># Routes — clean, expressive, familiar</span>
Route.resource(<span class="code-string">"posts"</span>, PostController)
Route.get(<span class="code-string">"/dashboard"</span>, [HomeController, <span class="code-string">"index"</span>])
    .middleware(<span class="code-string">"auth"</span>)</code></pre>
        </div>
    </div>

    <!-- Quick Start Section -->
    <section class="section-quickstart" id="quickstart">
        <div class="section-container">
            <div class="section-header">
                <span class="section-tag">Get Started</span>
                <h2 class="section-title">Up and Running in Seconds</h2>
                <p class="section-description">
                    From zero to a running application with migrations and seed data — just four commands.
                </p>
            </div>
            <div class="quickstart-grid">
                <div class="quickstart-step">
                    <div class="step-number">1</div>
                    <div class="step-content">
                        <h3>Install & Configure</h3>
                        <div class="step-code">
                            <code>cp .env.example .env</code>
                            <code>python dev.py key:generate</code>
                        </div>
                    </div>
                </div>
                <div class="quickstart-step">
                    <div class="step-number">2</div>
                    <div class="step-content">
                        <h3>Migrate & Seed</h3>
                        <div class="step-code">
                            <code>python dev.py migrate --seed</code>
                        </div>
                    </div>
                </div>
                <div class="quickstart-step">
                    <div class="step-number">3</div>
                    <div class="step-content">
                        <h3>Serve</h3>
                        <div class="step-code">
                            <code>python dev.py serve</code>
                        </div>
                    </div>
                </div>
                <div class="quickstart-step">
                    <div class="step-number">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    </div>
                    <div class="step-content">
                        <h3>Or Use Docker</h3>
                        <div class="step-code">
                            <code>docker compose up -d --build</code>
                        </div>
                        <p class="step-note">App available at <strong>localhost:8300</strong></p>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Why Craft Feature Grid -->
    <section class="section-features" id="features">
        <div class="section-container">
            <div class="section-header">
                <span class="section-tag">Why Craft?</span>
                <h2 class="section-title">Everything You Need, Nothing You Don't</h2>
                <p class="section-description">
                    A full-featured framework that respects your time. familiar MVC conventions adapted for Python developers who demand clarity and power.
                </p>
            </div>
            <div class="features-grid">
                <!-- Feature 1 -->
                <div class="feature-card" id="feature-orm">
                    <div class="feature-icon feature-icon-orange">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>
                    </div>
                    <h3>Craft ORM</h3>
                    <p>Active Record with eager loading, relationships, soft deletes and a fluent query builder — expressive, and Pythonic.</p>
                </div>
                <!-- Feature 2 -->
                <div class="feature-card" id="feature-perf">
                    <div class="feature-icon feature-icon-blue">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
                    </div>
                    <h3>Exceptional Performance</h3>
                    <p>Built on Starlette's ASGI engine. Async-ready from the ground up, with sub-millisecond middleware overhead.</p>
                </div>
                <!-- Feature 3 -->
                <div class="feature-card" id="feature-migrations">
                    <div class="feature-icon feature-icon-green">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path></svg>
                    </div>
                    <h3>Schema & Migrations</h3>
                    <p>Fluent DDL builder with batches, rollback, and pretend mode. SQLite, PostgreSQL, and MySQL — same SQL everywhere.</p>
                </div>
                <!-- Feature 4 -->
                <div class="feature-card" id="feature-auth">
                    <div class="feature-icon feature-icon-purple">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                    </div>
                    <h3>Authentication & Authorization</h3>
                    <p>Bcrypt passwords, session guards, CSRF protection, Gates & Policies. Deny-by-default, timing-safe comparisons.</p>
                </div>
                <!-- Feature 5 -->
                <div class="feature-card" id="feature-views">
                    <div class="feature-icon feature-icon-pink">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
                    </div>
                    <h3>Forge Template Engine</h3>
                    <p>Jinja2 powered with Forge directives for conditionals, loops, extends, sections, CSRF, auth guards — all familiar syntax.</p>
                </div>
                <!-- Feature 6 -->
                <div class="feature-card" id="feature-cli">
                    <div class="feature-icon feature-icon-amber">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>
                    </div>
                    <h3>Craft CLI</h3>
                    <p>12 generators, migrate, seed, tinker, serve, queue work — a complete console for Python. dev.py does it all.</p>
                </div>
            </div>
        </div>
    </section>

<!-- CTA Cards Section (CodeIgniter-style action cards) -->
    <section class="section-cards" id="resources">
        <div class="section-container">
            <div class="cards-grid">
                <a href="/docs/installation" class="action-card" id="card-download">
                    <div class="card-icon-wrapper card-icon-orange">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                    </div>
                    <h3>Download & Install</h3>
                    <p>Get the latest release and start building immediately.</p>
                </a>
                <a href="/docs" class="action-card" id="card-docs">
                    <div class="card-icon-wrapper card-icon-blue">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>
                    </div>
                    <h3>Clear Documentation</h3>
                    <p>Comprehensive guides covering every feature of the framework.</p>
                </a>
                <a href="/posts" class="action-card" id="card-community">
                    <div class="card-icon-wrapper card-icon-green">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                    </div>
                    <h3>Get Support & Discuss</h3>
                    <p>Join the community forum and share your experience.</p>
                </a>
                <a href="/docs/testing" class="action-card" id="card-contribute">
                    <div class="card-icon-wrapper card-icon-purple">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    </div>
                    <h3>Tested on Every Target</h3>
                    <p>530 tests across SQLite, PostgreSQL and the minimum Python version.</p>
                </a>
            </div>
        </div>
    </section>

    <!-- Community / Recent Discussions -->
    <section class="section-community" id="community">
        <div class="section-container">
            <div class="section-header">
                <span class="section-tag">Community</span>
                <h2 class="section-title">{{ __('recent_posts') }}</h2>
            </div>
            @if(posts is defined and posts is not none and posts|length > 0)
                <div class="discussions-grid">
                    @foreach(posts as post)
                        {# The route is /posts/{id}, so the parameter must be `id` —
                           passing `post` left the placeholder unsubstituted. #}
                        <a href="{{ route('posts.show', id=post.get_attribute('id')) }}" class="discussion-item">
                            <div class="discussion-meta">
                                <span class="discussion-tag">Forum</span>
                                <span class="discussion-date">{{ (post.get_attribute('created_at') or '')|string|truncate(10, true, '') }}</span>
                            </div>
                            <h4 class="discussion-title">{{ post.get_attribute('title') }}</h4>
                            <p class="discussion-excerpt">{{ post.get_attribute('body') }}</p>
                        </a>
                    @endforeach
                </div>
            @else
                <div class="discussions-empty">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                    <p>No active discussions yet. <a href="/posts/create">Start one →</a></p>
                </div>
            @endif
        </div>
    </section>
@endsection
