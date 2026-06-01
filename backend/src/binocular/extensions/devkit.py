"""Module Dev Kit CLI tool for local static and runtime verification."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

from binocular.extensions.contract import ModuleCheckInput
from binocular.extensions.loader import ModuleLoader
from binocular.extensions.runner import ModuleRunner
from binocular.scraping.client import ScrapeClient


def mock_handler(request: httpx.Request) -> httpx.Response:
    """Mock HTTP transport returning a sample HTML response with version 2.5.0."""

    html = (
        "<html>\n"
        "  <head><title>Firmware Updates</title></head>\n"
        "  <body>\n"
        "    <h1>Device Support</h1>\n"
        "    <div class='version-info'>\n"
        "      <span class='label'>Latest Version:</span>\n"
        "      <span class='value'>2.5.0</span>\n"
        "    </div>\n"
        "  </body>\n"
        "</html>\n"
    )
    return httpx.Response(
        200,
        headers={"Content-Type": "text/html; charset=utf-8"},
        content=html.encode("utf-8"),
        request=request,
    )


class DevKitCLI:
    """Command-line interface for the Binocular Module Dev Kit."""

    def __init__(self) -> None:
        self.parser = argparse.ArgumentParser(
            prog="python -m binocular.extensions.devkit",
            description="Binocular Module Dev Kit: validate and run extension modules locally.",
        )
        self.subparsers = self.parser.add_subparsers(dest="command", required=True)
        self._add_check_parser()
        self._add_run_parser()

    def _add_check_parser(self) -> None:
        check_parser = self.subparsers.add_parser(
            "check",
            help="Statically check if a module conforms to the authoring contract.",
        )
        check_parser.add_argument(
            "module_path",
            type=str,
            help="Path to the extension module Python file.",
        )
        check_parser.add_argument(
            "--json",
            action="store_true",
            help="Output validation results in JSON format.",
        )

    def _add_run_parser(self) -> None:
        run_parser = self.subparsers.add_parser(
            "run",
            help="Statically check and execute a module's firmware check logic.",
        )
        run_parser.add_argument(
            "module_path",
            type=str,
            help="Path to the extension module Python file.",
        )
        run_parser.add_argument(
            "--device-type",
            type=str,
            required=True,
            help="The device type being checked.",
        )
        run_parser.add_argument(
            "--model",
            type=str,
            required=True,
            help="The device model name.",
        )
        run_parser.add_argument(
            "--current-version",
            type=str,
            required=True,
            help="The recorded current firmware version.",
        )
        run_parser.add_argument(
            "--url",
            type=str,
            default=None,
            help="The target firmware page URL (omitting uses offline MockTransport).",
        )
        run_parser.add_argument(
            "--extra",
            type=str,
            default=None,
            help="Comma-separated extra key=value settings to inject.",
        )
        run_parser.add_argument(
            "--timeout",
            type=float,
            default=10.0,
            help="Timeout limit in seconds for runtime execution.",
        )
        run_parser.add_argument(
            "--json",
            action="store_true",
            help="Output execution results in JSON format.",
        )

    def run_cli(self, args_list: list[str] | None = None) -> int:
        """Parse arguments and route execution to appropriate subcommand."""

        args = self.parser.parse_args(args_list)
        module_path = Path(args.module_path)

        if args.command == "check":
            return self.cmd_check(module_path, output_json=args.json)
        elif args.command == "run":
            extras = self._parse_extras(args.extra)
            return asyncio.run(
                self.cmd_run(
                    path=module_path,
                    device_type=args.device_type,
                    model=args.model,
                    current_version=args.current_version,
                    url=args.url,
                    extra=extras,
                    timeout=args.timeout,
                    output_json=args.json,
                )
            )
        return 1

    def cmd_check(self, path: Path, output_json: bool = False) -> int:
        """Execute static verification for a module file."""

        loader = ModuleLoader(path.parent)
        result = loader.load(path)

        if result.success:
            assert result.loaded_module is not None
            meta = result.loaded_module.metadata
            if output_json:
                print(
                    json.dumps(
                        {
                            "status": "passed",
                            "module_id": meta.module_id,
                            "display_name": meta.display_name,
                            "version": meta.version,
                            "author": meta.author,
                        }
                    )
                )
            else:
                print("✓ Static contract validation: PASSED")
                print(f"  Module ID:    {meta.module_id}")
                print(f"  Display Name: {meta.display_name}")
                print(f"  Version:      {meta.version or '—'}")
                print(f"  Author:       {meta.author or '—'}")
            return 0

        assert result.failure is not None
        if output_json:
            print(
                json.dumps(
                    {
                        "status": "failed",
                        "error_type": result.failure.error_type,
                        "message": result.failure.message,
                    }
                )
            )
        else:
            print("✗ Static contract validation: FAILED", file=sys.stderr)
            print(f"  Error Type:   {result.failure.error_type}", file=sys.stderr)
            print(f"  Message:      {result.failure.message}", file=sys.stderr)
        return 1

    async def cmd_run(
        self,
        path: Path,
        device_type: str,
        model: str,
        current_version: str,
        url: str | None,
        extra: dict[str, str],
        timeout: float,
        output_json: bool = False,
    ) -> int:
        """Run static verification followed by asynchronous check execution."""

        loader = ModuleLoader(path.parent)
        load_result = loader.load(path)

        if not load_result.success:
            assert load_result.failure is not None
            if output_json:
                print(
                    json.dumps(
                        {
                            "status": "failed",
                            "phase": "static",
                            "error_type": load_result.failure.error_type,
                            "message": load_result.failure.message,
                        }
                    )
                )
            else:
                print(
                    f"✗ Static verification failed: {load_result.failure.message}",
                    file=sys.stderr,
                )
            return 1

        assert load_result.loaded_module is not None
        loaded_module = load_result.loaded_module

        # Setup standard polite ScrapeClient
        target_url = url or "http://local-mock-scraping-server.test/firmware.html"
        use_mock = url is None

        transport = httpx.MockTransport(mock_handler) if use_mock else None
        scrape_client = ScrapeClient(
            user_agent="BinocularDevKit/1.0 (Local Test; polite)",
            timeout_seconds=timeout,
            rate_limit_interval_seconds=1.0,
            max_retries=1,
            backoff_base_seconds=1.0,
            transport=transport,
        )

        check_input = ModuleCheckInput(
            device_type=device_type,
            model=model,
            current_version=current_version,
            source_url=target_url,
            extra=extra,
        )

        runner = ModuleRunner(timeout_seconds=timeout)

        try:
            run_result = await runner.run(loaded_module, check_input, scrape_client)
        finally:
            await scrape_client.aclose()

        if run_result.status == "success":
            if output_json:
                print(run_result.model_dump_json())
            else:
                print("✓ Module Execution: SUCCESS")
                print(f"  Latest Version: {run_result.latest_version}")
                print(f"  Detail:         {run_result.detail or '—'}")
                print(f"  Source URL:     {run_result.source_url or '—'}")
                if run_result.diagnostics:
                    print("  Diagnostics:")
                    for k, v in run_result.diagnostics.items():
                        print(f"    - {k}: {v}")
            return 0

        if output_json:
            print(run_result.model_dump_json())
        else:
            print("✗ Module Execution: FAILED", file=sys.stderr)
            print(f"  Detail:         {run_result.detail}", file=sys.stderr)
            if run_result.diagnostics:
                print("  Diagnostics:", file=sys.stderr)
                for k, v in run_result.diagnostics.items():
                    print(f"    - {k}: {v}", file=sys.stderr)
        return 1

    @staticmethod
    def _parse_extras(extras_str: str | None) -> dict[str, str]:
        """Convert a comma-separated key=value string into a dict."""

        if not extras_str:
            return {}
        result = {}
        for pair in extras_str.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                result[k.strip()] = v.strip()
        return result


if __name__ == "__main__":
    cli = DevKitCLI()
    sys.exit(cli.run_cli())
