"""
Master pipeline for WSN figures and tables generation.

Usage:
    python src/run_pipeline.py              # Generate everything
    python src/run_pipeline.py --figures     # Figures only
    python src/run_pipeline.py --tables      # Tables only
    python src/run_pipeline.py --report      # Statistical report only
"""
import argparse
import sys
import traceback
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_parser import ExperimentDataParser, load_all_data
from src.analysis.statistical_analysis import StatisticalAnalyzer
from src.pipeline_logger import PipelineLogger


def main():
    parser = argparse.ArgumentParser(description='WSN Figures & Tables Pipeline')
    parser.add_argument('--figures', action='store_true', help='Generate figures only')
    parser.add_argument('--tables', action='store_true', help='Generate tables only')
    parser.add_argument('--report', action='store_true', help='Statistical report only')
    parser.add_argument('--data-dir', type=str, default=None,
                        help='Path to experiment data directory')
    args = parser.parse_args()
    
    run_all = not (args.figures or args.tables or args.report)
    
    # Setup pipeline logger
    log_dir = str(Path(__file__).parent.parent / "output" / "logs")
    pipe_logger = PipelineLogger(log_dir, "run_pipeline")
    
    pipe_logger.log_config({
        "mode": "all" if run_all else (
            "figures" if args.figures else
            "tables" if args.tables else "report"
        ),
        "data_dir": args.data_dir or "auto-detect",
    })
    
    exit_code = 0
    try:
        # Load data
        pipe_logger.log_section("Data Loading")
        t0 = datetime.now()
        data_root = Path(args.data_dir) if args.data_dir else None
        data = load_all_data(data_root)
        
        data_info = {}
        for key, df in data.items():
            if hasattr(df, '__len__'):
                data_info[key] = len(df) if hasattr(df, '__len__') else 0
            elif isinstance(df, dict):
                data_info[key] = len(df)
        pipe_logger.log_data_loaded(data_info)
        
        if not data or all(len(v) == 0 if hasattr(v, '__len__') else not v
                          for v in data.values() if v is not None):
            pipe_logger.warning(
                "No experiment data found. Run wsn-experiment first to generate data."
            )
            pipe_logger.info("  cd ../WSN-Experiment && python run_experiment.py")
        
        pipe_logger.log_phase("Data loading", (datetime.now() - t0).total_seconds(),
                              "PASS" if data else "WARN")
        
        # Generate figures
        if run_all or args.figures:
            pipe_logger.log_section("Figure Generation")
            t0 = datetime.now()
            try:
                from src.figures.generate_all_figures import generate_all as gen_figs
                fig_paths = gen_figs(data_root)
                
                if fig_paths:
                    for name, path in fig_paths.items() if isinstance(fig_paths, dict) else []:
                        pipe_logger.log_figure(name, str(path))
                else:
                    pipe_logger.log_figure("all_figures", "see output/figures/", "OK")
                
                pipe_logger.log_phase("Figure generation", (datetime.now() - t0).total_seconds(), "PASS")
            except Exception as e:
                pipe_logger.error(f"Figure generation failed: {e}")
                pipe_logger.debug(traceback.format_exc())
                pipe_logger.log_phase("Figure generation", (datetime.now() - t0).total_seconds(), "FAIL")
                exit_code = 1
        
        # Generate tables
        if run_all or args.tables:
            pipe_logger.log_section("Table Generation")
            t0 = datetime.now()
            try:
                from src.tables.generate_all_tables import generate_all as gen_tabs
                tab_paths = gen_tabs(data_root)
                
                if tab_paths:
                    for name, path in tab_paths.items() if isinstance(tab_paths, dict) else []:
                        pipe_logger.log_table(name, str(path))
                else:
                    pipe_logger.log_table("all_tables", "see output/tables/", "OK")
                
                pipe_logger.log_phase("Table generation", (datetime.now() - t0).total_seconds(), "PASS")
            except Exception as e:
                pipe_logger.error(f"Table generation failed: {e}")
                pipe_logger.debug(traceback.format_exc())
                pipe_logger.log_phase("Table generation", (datetime.now() - t0).total_seconds(), "FAIL")
                exit_code = 1
        
        # Statistical report
        if run_all or args.report:
            pipe_logger.log_section("Statistical Analysis")
            t0 = datetime.now()
            try:
                if data:
                    analyzer = StatisticalAnalyzer(data)
                    report = analyzer.full_report(scale=300)
                    
                    # Save report
                    report_path = Path(__file__).parent.parent / 'output' / 'statistical_report.txt'
                    report_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(report_path, 'w') as f:
                        f.write(report)
                    
                    pipe_logger.info(f"  Report saved to: {report_path}")
                    pipe_logger.info("")
                    # Log report summary lines to debug
                    for line in report.strip().split('\n'):
                        pipe_logger.debug(f"  {line}")
                    
                    pipe_logger.log_phase("Statistical analysis", (datetime.now() - t0).total_seconds(), "PASS")
                else:
                    pipe_logger.warning("No data available for statistical analysis.")
                    pipe_logger.log_phase("Statistical analysis", (datetime.now() - t0).total_seconds(), "SKIP")
            except Exception as e:
                pipe_logger.error(f"Statistical analysis failed: {e}")
                pipe_logger.debug(traceback.format_exc())
                pipe_logger.log_phase("Statistical analysis", (datetime.now() - t0).total_seconds(), "FAIL")
                exit_code = 1
        
    except Exception as e:
        pipe_logger.error(f"Pipeline failed: {e}")
        pipe_logger.debug(traceback.format_exc())
        exit_code = 1
    
    pipe_logger.finalize(exit_code)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()