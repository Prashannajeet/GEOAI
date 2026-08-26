import importlib.util
import sys
from pathlib import Path


def main():
    source = Path(__file__).with_name("streamlit_app.py").read_text()
    marker = "st.set_page_config("
    module_source = source[: source.index(marker)]
    spec = importlib.util.spec_from_loader("streamlit_core_smoke", loader=None)
    module = importlib.util.module_from_spec(spec)
    module.__dict__["__file__"] = str(Path(__file__).with_name("streamlit_app.py"))
    exec(module_source, module.__dict__)

    result = module.analyze(2017, 2024, 0.18, 120)
    print(f"hotspots={len(result['features'])}")
    print(f"mean_change={result['metadata']['meanChange']:.4f}")
    print(f"max_change={result['metadata']['maxChange']:.4f}")


if __name__ == "__main__":
    sys.exit(main())
