{#
    API reference — the OpenAPI viewer.

    A standalone HTML document (it deliberately does not extend the app layout,
    so the viewer owns the whole page). It reads the spec the application serves
    and renders it for browsing.
#}
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <title>SoftPax API Docs — Craft Framework</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.11.0/swagger-ui.min.css">
</head>
<body>
    <div id="swagger"></div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.11.0/swagger-ui-bundle.min.js"></script>
    <script>
        window.onload = () => SwaggerUIBundle({ url: '/docs/oauth2-redirect', dom_id: '#swagger' });
    </script>
</body>
</html>
