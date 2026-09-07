<?php

return [
    // Where the Python runtime writes run artifacts. The workbench only reads them.
    'artifact_root' => env('CCF6_ARTIFACT_ROOT', base_path('artifacts')),

    // The Cognitive runtime, when it is running as a service (ADR-0008).
    'runtime_url' => env('CCF6_RUNTIME_URL', 'http://runtime:8931'),
];
