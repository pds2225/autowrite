from app import parse_args, run_pipeline

if __name__ == "__main__":
    args = parse_args()
    run_pipeline(args.template, args.content, args.tables, args.images, args.output_docx, args.output_dir)
