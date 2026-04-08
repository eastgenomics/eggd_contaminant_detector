import textwrap


def preprocess() -> str:
    script = textwrap.dedent("""
        set -e -x
        bcftools_norm() {
            local VCF=$1
            local REFERENCE=$2
            local STEM=$(dirname -- $(readlink -e "$VCF"))
            local NAME=$(basename -- "$VCF" .vcf.gz)
            local OUT="${STEM}/${NAME}.norm.vcf.gz"
            bcftools norm -m-any -f "$REFERENCE" -d all -W=tbi -Oz -o "$OUT" "$VCF"
            echo "$OUT"
        }
        
        bcftools_sort() {
            local VCF=$1
            local STEM=$(dirname -- $(readlink -e "$VCF"))
            local NAME=$(basename -- "$VCF" .vcf.gz)
            local OUT="${STEM}/${NAME}.sorted.vcf.gz"
            bcftools sort -W=tbi -Oz -o "$OUT" "$VCF"
            echo "$OUT"
        }
                             
        preprocess() {
            local VCF=$1
            local REFERENCE=$2
            local NORMED_VCF=$(bcftools_norm "$VCF" "$REFERENCE")
            local SORTED_VCF=$(bcftools_sort "$NORMED_VCF")
            echo "$SORTED_VCF"
        }
        
        loop_preprocess(){
            local FILELIST=$1
            local REFERENCE=$2
            local TMP_FILELIST="/in/tmp_$(basename $FILELIST)"
            while read -r VCF; do
                preprocess "$VCF" "$REFERENCE" >> "$TMP_FILELIST"
            done < "$FILELIST"
            mv "$TMP_FILELIST" "$FILELIST"
        }
        
        REFERENCE=$(cat "/in/reference.txt")
        loop_preprocess "/in/truths.txt" "$REFERENCE"
        loop_preprocess "/in/querys.txt" "$REFERENCE"
    """).strip()
    return script


def sompy() -> str:
    script = textwrap.dedent("""
        set -e -x
        mapfile -t TRUTH_VCFS < /in/truths.txt
        mapfile -t QUERY_VCFS < /in/querys.txt
        REFERENCE=$(cat /in/reference.txt)
        PANEL_BED=$([ -e "/in/panel.txt" ] && cat /in/panel.txt || true)

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
            T_NAME=$(basename "$TRUTH" | sed -E 's/(.norm.sorted.vcf.gz|.vcf.gz)$//')
            for QUERY in "${QUERY_VCFS[@]}"; do
                Q_NAME=$(basename "$QUERY" | sed -E 's/(.norm.sorted.vcf.gz|.vcf.gz)$//')
                /opt/hap.py/bin/som.py "${ARGS[@]}" -o "/out/${T_NAME}_${Q_NAME}" "$TRUTH" "$QUERY"
            done
        done
    """).strip()
    return script
