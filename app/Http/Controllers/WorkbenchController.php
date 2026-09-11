<?php

namespace App\Http\Controllers;

use Illuminate\Support\Facades\File;
use Illuminate\Support\Str;
use Illuminate\View\View;

/**
 * The workbench reads run artifacts. It does not own them and it does not compute
 * anything the runtime could have computed: every number on screen was written by
 * the Python runtime and is read back verbatim (ADR-0007).
 */
class WorkbenchController extends Controller
{
    private const FUNCTIONAL_WEB_FILES = [
        'definition.json',
        'manifest.json',
        'dataset.json',
        'topology.npz',
        'presentations.jsonl',
        'learning.npz',
        'activity.npz',
        'basins.json',
        'webs.json',
        'cardinals.json',
        'metrics.json',
        'aggregate.json',
        'summary.json',
    ];

    private function root(): string
    {
        return rtrim(config('ccf6.artifact_root', base_path('artifacts')), '/');
    }

    /** Every run on disk, newest first. */
    public function index(): View
    {
        $runs = collect(File::directories($this->root()))
            ->map(fn ($dir) => $this->manifest($dir))
            ->filter()
            ->sortByDesc('started')
            ->values();

        return view('workbench.index', ['runs' => $runs]);
    }

    public function show(string $run): View
    {
        $dir = $this->root().'/'.basename($run);
        abort_unless(File::isDirectory($dir), 404);

        $manifest = $this->manifest($dir);
        $problem = $this->artifactProblem($dir, $manifest);
        if ($problem !== null) {
            return view('workbench.unsupported', [
                'run' => basename($run),
                'manifest' => $manifest,
                'problem' => $problem,
            ]);
        }
        $summary = $this->json($dir.'/summary.json') ?? [];

        if (($manifest['contract'] ?? null) === 'ncl-functional-web-v1') {
            if (($manifest['kind'] ?? null) === 'synthetic_lexical_grounding') {
                return view('workbench.domain', [
                    'run' => basename($run),
                    'manifest' => $manifest,
                    'summary' => $summary,
                    'dataset' => $this->json($dir.'/dataset.json') ?? [],
                ]);
            }

            if (($manifest['kind'] ?? null) === 'zero_rest_network') {
                return view('workbench.network', [
                    'run' => basename($run),
                    'manifest' => $manifest,
                    'summary' => $summary,
                    'topology' => $this->json($dir.'/topology.json') ?? [],
                    'activity' => $this->json($dir.'/activity.json') ?? [],
                ]);
            }

            if (($manifest['kind'] ?? null) === 'coordinated_presentation') {
                return view('workbench.presentation', [
                    'run' => basename($run),
                    'manifest' => $manifest,
                    'summary' => $summary,
                    'topology' => $this->json($dir.'/topology.json') ?? [],
                    'presentations' => $this->jsonLines($dir.'/presentations.jsonl'),
                ]);
            }

            if (in_array($manifest['kind'] ?? null, ['success_gated_learning', 'recruitment_homeostasis'], true)) {
                return view('workbench.learning', [
                    'run' => basename($run),
                    'manifest' => $manifest,
                    'summary' => $summary,
                    'learning' => $this->json($dir.'/learning.json') ?? [],
                ]);
            }

            if (($manifest['kind'] ?? null) === 'replicated_milestone') {
                return view('workbench.aggregate', [
                    'run' => basename($run),
                    'manifest' => $manifest,
                    'summary' => $summary,
                    'metrics' => $this->json($dir.'/metrics.json') ?? [],
                    'aggregate' => $this->json($dir.'/aggregate.json') ?? [],
                    'artifacts' => collect($manifest['files'])->map(fn (string $name): array => [
                        'name' => $name,
                        'bytes' => File::size($dir.'/'.$name),
                        'checksum' => $manifest['checksums'][$name] ?? null,
                    ]),
                ]);
            }

            if (in_array($manifest['kind'] ?? null, ['matched_target_basins', 'completion_reactivation', 'functional_web_detection', 'cardinal_classification'], true)) {
                return view('workbench.basins', [
                    'run' => basename($run),
                    'manifest' => $manifest,
                    'summary' => $summary,
                    'arms' => $this->json($dir.'/arms.json') ?? [],
                    'basins' => $this->json($dir.'/basins.json') ?? [],
                    'completion' => $this->json($dir.'/evaluation.json') ?? [],
                    'webs' => $this->json($dir.'/webs.json') ?? [],
                    'cardinals' => $this->json($dir.'/cardinals.json') ?? [],
                ]);
            }
        }

        return view('workbench.unsupported', [
            'run' => basename($run),
            'manifest' => $manifest,
            'problem' => 'The artifact kind is not supported by this workbench.',
        ]);
    }

    /** A document from docs/, rendered. The file on disk stays the source of truth. */
    public function doc(string $page): View
    {
        $path = base_path('docs/'.basename($page).'.md');
        abort_unless(File::exists($path), 404);

        return view('workbench.doc', [
            'title' => Str::of(File::get($path))->before("\n")->ltrim('# ')->toString(),
            'body' => Str::markdown(File::get($path)),
        ]);
    }

    private function manifest(string $dir): array
    {
        $manifest = $this->json($dir.'/manifest.json');

        return $manifest
            ? $manifest + ['run' => basename($dir)]
            : [
                'run' => basename($dir),
                'name' => 'Malformed artifact',
                'started' => null,
                'malformed' => true,
            ];
    }

    private function artifactProblem(string $dir, array $manifest): ?string
    {
        if ($manifest['malformed'] ?? false) {
            return 'manifest.json is missing or malformed.';
        }
        if (($manifest['contract'] ?? null) !== 'ncl-functional-web-v1') {
            return 'The artifact contract is unsupported by the NCL-only workbench.';
        }
        if (! is_array($manifest['files'] ?? null)) {
            return 'The manifest has no readable file inventory.';
        }
        if (($manifest['kind'] ?? null) === 'replicated_milestone') {
            if ($manifest['files'] !== self::FUNCTIONAL_WEB_FILES) {
                return 'The milestone artifact inventory is incomplete.';
            }
            foreach (['digest', 'software_version', 'status'] as $field) {
                if (! is_string($manifest[$field] ?? null) || $manifest[$field] === '') {
                    return 'The milestone manifest is missing '.$field.'.';
                }
            }
            $expectedChecksums = array_values(array_diff(
                self::FUNCTIONAL_WEB_FILES,
                ['manifest.json'],
            ));
            if (
                ! is_array($manifest['checksums'] ?? null)
                || array_keys($manifest['checksums']) !== $expectedChecksums
            ) {
                return 'The milestone checksum inventory is incomplete.';
            }
        }
        $readableJson = match ($manifest['kind'] ?? null) {
            'synthetic_lexical_grounding' => ['summary.json', 'dataset.json'],
            'zero_rest_network' => ['summary.json', 'topology.json', 'activity.json'],
            'coordinated_presentation' => ['summary.json', 'topology.json'],
            'success_gated_learning', 'recruitment_homeostasis' => ['summary.json', 'learning.json'],
            'replicated_milestone' => ['summary.json', 'metrics.json', 'aggregate.json'],
            'matched_target_basins', 'completion_reactivation',
            'functional_web_detection', 'cardinal_classification' => [
                'summary.json', 'arms.json', 'basins.json', 'evaluation.json',
                'webs.json', 'cardinals.json',
            ],
            default => ['summary.json'],
        };
        foreach ($manifest['files'] as $name) {
            if (! is_string($name) || basename($name) !== $name) {
                return 'The manifest contains an invalid file name.';
            }
            $path = $dir.'/'.$name;
            if (! File::isFile($path)) {
                return $name.' is missing.';
            }
            if (
                isset($manifest['checksums'][$name])
                && hash_file('sha256', $path) !== $manifest['checksums'][$name]
            ) {
                return $name.' does not match its recorded checksum.';
            }
            if (in_array($name, $readableJson, true) && $this->json($path) === null) {
                return $name.' is malformed.';
            }
        }

        return null;
    }

    private function json(string $path): ?array
    {
        if (! File::exists($path)) {
            return null;
        }
        $decoded = json_decode(File::get($path), true);

        return is_array($decoded) && json_last_error() === JSON_ERROR_NONE
            ? $decoded
            : null;
    }

    /** @return list<array<string, mixed>> */
    private function jsonLines(string $path): array
    {
        if (! File::exists($path)) {
            return [];
        }

        return array_values(array_map(
            fn (string $line): array => json_decode($line, true),
            array_filter(explode("\n", File::get($path))),
        ));
    }
}
