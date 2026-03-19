import textwrap

def bcftools_norm() -> str:
    script = textwrap.dedent("""
        set -e
        bcftools_norm() {
            local VCF=$1
            local REFERENCE=$2
            STEM=$(dirname -- $(readlink -e "$VCF"))
            NAME=$(basename -- "$VCF" .vcf.gz)
            bcftools norm -m-any -f "$REFERENCE" "$VCF" | \
                bcftools norm -d any -W=tbi -Oz -o "${STEM}/${NAME}.norm.vcf.gz" "$VCF"
        }

        TRUTH_VCFS=($(find /in/truths -type f -name "*.vcf.gz"))
        QUERY_VCFS=($(find /in/queries -type f -name "*.vcf.gz"))
        REFERENCE=$(find /in/reference -type f ! -name "*.fai" ! -name "*.gzi" | head -n 1)
        for TRUTH in "${TRUTH_VCFS[@]}"; do
            bcftools_norm "$TRUTH" "$REFERENCE"
        done
        for QUERY in "${QUERY_VCFS[@]}"; do
            bcftools_norm "$QUERY" "$REFERENCE"
        done
    """).strip()
    return script

def bcftools_sort() -> str:
    script = textwrap.dedent("""
        set -e
        bcftools_sort() {
            local VCF=$1
            local REFERENCE=$2
            STEM=$(dirname -- $(readlink -e "$VCF"))
            NAME=$(basename -- "$VCF" .vcf.gz)
            bcftools norm -m-any -f "$REFERENCE" "$VCF" | \
                bcftools norm -d any -W=tbi -Oz -o "${STEM}/${NAME}.norm.vcf.gz" "$VCF"
        }
            local VCF=$1
            NAME=$(basename "$VCF" .vcf.gz)
            bcftools sort -W=tbi -Oz -o /in/truths/"${NAME}.sorted.vcf.gz" "$TRUTH"
        }
        TRUTH_VCFS=($(find /in/truths -type f -name "*.vcf.gz"))
        QUERY_VCFS=($(find /in/queries -type f -name "*.vcf.gz"))
        for TRUTH in "${TRUTH_VCFS[@]}"; do
            NAME=$(basename "$TRUTH" .vcf.gz)
            bcftools sort -W=tbi -Oz -o /in/truths/"${NAME}.sorted.vcf.gz" "$TRUTH"
        done
        for QUERY in "${QUERY_VCFS[@]}"; do
            NAME=$(basename "$QUERY" .vcf.gz)
            bcftools sort -W=tbi -Oz -o /in/queries/"${NAME}.sorted.vcf.gz" "$QUERY"
        done
    """).strip()
    return script

def sompy() -> str:
    script = textwrap.dedent("""
        set -e
        TRUTH_VCFS=($(find /in/truths -type f -name "*sorted.vcf.gz"))
        QUERY_VCFS=($(find /in/queries -type f -name "*sorted.vcf.gz"))
        REFERENCE=$(find /in/reference -type f ! -name "*.fai" ! -name "*.gzi" | head -n 1)
        PANEL_BED=$( [ -d "/in/panel_bed" ] && find "/in/panel_bed" -type f -name "*.bed*" | head -n 1 )

        ARGS=(
            --no-count-unk
            --no-fixchr-truth
            --no-fixchr-query
            --include-nonpass
            --reference "$REFERENCE"
        )
        
        if [[ -n "$PANEL_BED" ]]; then
            ARGS+=(--restrict-regions "$PANEL_BED")
        fi
        
        for TRUTH in "${TRUTH_VCFS[@]}"; do
            T_NAME=$(basename "$TRUTH" .sorted.vcf.gz)
            for QUERY in "${QUERY_VCFS[@]}"; do
                Q_NAME=$(basename "$QUERY" .sorted.vcf.gz)
                /opt/hap.py/bin/som.py "${ARGS[@]}" -o "/out/${T_NAME}_${Q_NAME}" "$TRUTH" "$QUERY"
            done
        done
    """).strip()
    return script