"""boogh cli is argument parsing over the op registry."""
import json
import sys
import urllib.error

from boogh import ops


def main():
    parser, core = ops.build()
    args = parser.parse_args()
    try:
        out = ops.run(core, args._route, args)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.HTTPError as e:
        print(json.dumps({"http": e.code, "body": e.read().decode()[:1000]},
                         ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
