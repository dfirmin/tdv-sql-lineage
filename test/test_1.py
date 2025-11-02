import sys
import traceback
from os.path import dirname, join, abspath
import ccw_etl_library as ccw

sys.path.append(dirname(dirname(__file__)))
from read_config import ReadConfig


def trunc_src_cd_val_xwalk(common_config):
    trunc_src_cd_val_xwalk = ccw.Statement(
        statement=""" DELETE FROM """ + common_config[
            'stg_dbname'] + """.SRC_CD_VAL_XWALK;""")
    return trunc_src_cd_val_xwalk


def vt_src_cd_val_xwalk(common_config):
    vt_src_cd_val_xwalk = ccw.Statement(statement="""
    CREATE VOLATILE TABLE vt_src_cd_val_xwalk (
        CDSET_UNQ_NM,
        XWALK_ROW_ID,
        SRC_DOMAIN_NM,
        TGT_SRC_DOMAIN_NM,
        SRC_CDSET_NM,
        CD_VAL_TXT,
        XWALK_BEG_DT,
        XWALK_END_DT,
        LOAD_CTL_KEY,
        SRC_CD_VAL_KEY,
        SRC_CDSET_KEY,
        CONFRM_CD_VAL_KEY,
        CONFRM_CDSET_NM,
        CONFRM_CD_VAL_TXT,
        CONFRM_CDSET_KEY,
        CONFRM_CDSET_ATTRIB_KEY,
        CHK_SUM_TXT,
        TRGT_KEY) AS
        (
        SELECT
        COALESCE(SRC.CDSET_UNQ_NM,' ') AS CDSET_UNQ_NM,
        COALESCE(SRC.XWALK_ROW_ID,' ') AS XWALK_ROW_ID,
        COALESCE(SRC.SRC_DOMAIN_NM,' ') AS SRC_DOMAIN_NM,
        COALESCE(TGT.SRC_DOMAIN_NM,' ') AS TGT_SRC_DOMAIN_NM,
        COALESCE(SRC.SRC_CDSET_NM,' ') AS SRC_CDSET_NM,
        COALESCE(SRC.CD_VAL_TXT,' ') AS CD_VAL_TXT,
        COALESCE(SRC.XWALK_BEG_DT ,TO_DATE ('0001-01-01', 'YYYY-MM-DD')) AS XWALK_BEG_DT,
        COALESCE(SRC.XWALK_END_DT,TO_DATE ('0001-01-01', 'YYYY-MM-DD')) AS XWALK_END_DT,
        SRC.LOAD_CTL_KEY,
        HASH_MD5(COALESCE(SRC.CD_VAL_TXT,' ')||'_'||COALESCE(SRC.SRC_DOMAIN_NM,' ')||'_'||COALESCE(SRC.SRC_CDSET_NM,' ')) AS SRC_CD_VAL_KEY,
        HASH_MD5(COALESCE(SRC.SRC_CDSET_NM,' ')||'_'||COALESCE(SRC.SRC_DOMAIN_NM,' ')) as SRC_CDSET_KEY,
        HASH_MD5(COALESCE(TGT.CD_VAL_TXT,' ')||'_'||COALESCE(TGT.SRC_DOMAIN_NM,' ')||'_'||COALESCE(TGT.SRC_CDSET_NM,' ')) AS CONFRM_CD_VAL_KEY,
        COALESCE(TGT.SRC_CDSET_NM,' ') as CONFRM_CDSET_NM,
        COALESCE(TGT.CD_VAL_TXT,' ') as CONFRM_CD_VAL_TXT,
        HASH_MD5(COALESCE(TGT.SRC_CDSET_NM,' ')||'_'||COALESCE(TGT.SRC_DOMAIN_NM,' ')) as CONFRM_CDSET_KEY,
		HASH_MD5(COALESCE(SRC.SRC_CDSET_NM,' ')||'_'||COALESCE(SRC.SRC_DOMAIN_NM,' ')||'_'||COALESCE(TGT.SRC_CDSET_NM,' ')) as CONFRM_CDSET_ATTRIB_KEY,
        ' ' as CHK_SUM_TXT,
        HASH_MD5(TO_CHAR(""" + common_config['load_ctl_key'] + """)||TO_CHAR(CURRENT_TIMESTAMP,'YYYY-MM-DD HH24:MI:SS')||'_'||COALESCE(SRC.CDSET_UNQ_NM,' ')||'_'||COALESCE(SRC.XWALK_ROW_ID,' ')||'_'||COALESCE(SRC.SRC_DOMAIN_NM,' ')||'_'||COALESCE(SRC.SRC_CDSET_NM,' ')||'_'||COALESCE(SRC.CD_VAL_TXT,' ')||'_'||COALESCE(SRC.XWALK_BEG_DT ,TO_DATE ('0001-01-01', 'YYYY-MM-DD'))||'_'||COALESCE(SRC.XWALK_END_DT,TO_DATE ('0001-01-01', 'YYYY-MM-DD'))||'_'||COALESCE(TGT.SRC_CDSET_NM,' ')||'_'||COALESCE(TGT.CD_VAL_TXT,' ')) as TRGT_KEY
        FROM """ + common_config['lz_dbname'] + """.CCW_CDSET_XWALK SRC INNER JOIN
        """ + common_config['lz_dbname'] + """.CCW_CDSET_XWALK TGT ON SRC.XWALK_ROW_ID(CASESPECIFIC) = TGT.XWALK_ROW_ID(CASESPECIFIC)
        AND SRC.XWALK_BEG_DT = TGT.XWALK_BEG_DT
        WHERE SRC.LOAD_CTL_KEY=""" + common_config['load_ctl_key'] + """
        AND TGT.LOAD_CTL_KEY=""" + common_config['load_ctl_key'] + """
        AND UPPER(SRC.SRC_TRGT_NM)='SOURCE'(CASESPECIFIC)
        AND UPPER(TGT.SRC_TRGT_NM)='TARGET'(CASESPECIFIC)
        AND SRC.XWALK_BEG_DT < SRC.XWALK_END_DT
        AND (SRC.CDSET_UNQ_NM <> 'PCW_0000_SR_CS229_SVC_TYPE_MJR_MNR_CD_XWALK' 
        OR SRC.SRC_CDSET_NM <> 'MS DRG Code' 
        OR SRC.CD_VAL_TXT <> '999')
                            )
                    WITH DATA 
                    ON 
                    COMMIT PRESERVE ROWS;""")
    return vt_src_cd_val_xwalk


# CONFRM_CDSET_ATTRIB_KEY used for Code Set to Crosswalk Ref Integrity specifically for the crosswalks:
# 'PCW_0000_SR_CS229a_SVC_TYPE_MJR_MNR_CD_XWALK' and 'PCW_0000_SR_CS229b_SVC_TYPE_MJR_MNR_CD_XWALK'
def vt_xwalk_ri_ref_attrib(common_config):
    vt_xwalk_ri_ref_attrib = ccw.Statement(statement="""
    CREATE VOLATILE TABLE vt_xwalk_ri_ref_attrib (
         REF_CDSET_KEY
        ,CDSET_ATTRIB_KEY
		,CDSET_UNQ_ID
		,CHNL_SRC_CD
                            ) AS
        (SELECT
         CDVAL.REF_CDSET_KEY
        ,HASH_MD5(COALESCE(CDSET.CDSET_NM,' ')||'_'||COALESCE(ATTRIB.CHNL_SRC_CD,' ')||'_'||COALESCE(ATTRIB.ATTRIB_NM,' ')) as CDSET_ATTRIB_KEY
		,CDSET.CDSET_UNQ_ID
		,CDSET.CHNL_SRC_CD
        FROM """ + common_config['base_dbname'] + """.REF_CD_ATTRIB ATTRIB
        LEFT JOIN """ + common_config['base_dbname'] + """.REF_CD_VAL CDVAL
        on ATTRIB.REF_CD_VAL_KEY = CDVAL.REF_CD_VAL_KEY
        AND CDVAL.CURR_RCD_IND = 'Y'
        LEFT JOIN """ + common_config['base_dbname'] + """.REF_CDSET CDSET
        on CDVAL.REF_CDSET_KEY = CDSET.REF_CDset_key
        AND CDSET.CURR_RCD_IND = 'Y'
        WHERE ATTRIB.CURR_RCD_IND = 'Y'
        GROUP  BY 1,2,3,4
                            )
                                                WITH DATA 
                    ON 
                    COMMIT PRESERVE ROWS;""")
    return vt_xwalk_ri_ref_attrib


def insert_src_cd_val_xwalk_stg_tbl(common_config):
    insert_src_cd_val_xwalk_stg_tbl = ccw.Statement(
        statement="""INSERT INTO """ + common_config['stg_dbname'] + """.SRC_CD_VAL_XWALK(
        CONFRM_CD_VAL_KEY, 
        SRC_CD_VAL_KEY,
        CRET_TS,
        UPDT_TS,
        CHNL_SRC_CD,
        CONFRM_CDSET_CHNL_SRC_CD,
        CURR_RCD_IND,
        CHK_SUM_TXT,
        LOAD_CTL_KEY,
        CONFRM_CDSET_NM,
        CONFRM_CD_VAL_TXT,
        SRC_CDSET_NM,
        SRC_CD_VAL_TXT,
        XWALK_ROW_ID,
        XWALK_UNQ_NM,
        CONFRM_CDSET_KEY,
        SRC_CDSET_KEY,
        CONFRM_CDSET_UNQ_ID,
        SRC_CDSET_UNQ_ID,
        XWALK_BEG_DT,
        XWALK_END_DT,
        EFF_DT,
        TERM_DT,
        CHNL_CD) 
SELECT	vt_src_cd_val_xwalk.CONFRM_CD_VAL_KEY,
        vt_src_cd_val_xwalk.SRC_CD_VAL_KEY,
        CURRENT_TIMESTAMP,
        CAST(CAST('9999/12/31' AS TIMESTAMP FORMAT 'YYYY/MM/DD') AS timestamp),
        CAST(vt_src_cd_val_xwalk.SRC_DOMAIN_NM AS VARCHAR(10)),
        CAST(vt_src_cd_val_xwalk.TGT_SRC_DOMAIN_NM AS VARCHAR(10)),
        CAST('Y' AS VARCHAR(1)),
        vt_src_cd_val_xwalk.CHK_SUM_TXT,
        vt_src_cd_val_xwalk.LOAD_CTL_KEY,
        vt_src_cd_val_xwalk.CONFRM_CDSET_NM,
        vt_src_cd_val_xwalk.CONFRM_CD_VAL_TXT,
        vt_src_cd_val_xwalk.SRC_CDSET_NM,
        vt_src_cd_val_xwalk.CD_VAL_TXT,
        vt_src_cd_val_xwalk.XWALK_ROW_ID,
        vt_src_cd_val_xwalk.CDSET_UNQ_NM,
        vt_src_cd_val_xwalk.CONFRM_CDSET_KEY,
        vt_src_cd_val_xwalk.SRC_CDSET_KEY,
        COALESCE(TGT_CDSET.CDSET_UNQ_ID, vt_xwalk_ri_ref_attrib.CDSET_UNQ_ID) AS CONFRM_CDSET_UNQ_ID,
        SRC_CDSET.CDSET_UNQ_ID AS SRC_CDSET_UNQ_ID,
        CAST(vt_src_cd_val_xwalk.XWALK_BEG_DT AS date),
        CAST(vt_src_cd_val_xwalk.XWALK_END_DT AS date),
        CAST(CURRENT_TIMESTAMP AS date),
        CAST(CURRENT_TIMESTAMP AS date),
        'INT' 
FROM	vt_src_cd_val_xwalk
LEFT JOIN """ + common_config['base_dbname'] + """.REF_CDSET SRC_CDSET
        ON vt_src_cd_val_xwalk.SRC_CDSET_KEY = SRC_CDSET.REF_CDSET_KEY
        AND SRC_CDSET.CURR_RCD_IND = 'Y'
LEFT JOIN """ + common_config['base_dbname'] + """.REF_CDSET TGT_CDSET
        ON vt_src_cd_val_xwalk.CONFRM_CDSET_KEY = TGT_CDSET.REF_CDSET_KEY
        AND TGT_CDSET.CURR_RCD_IND = 'Y'
LEFT JOIN vt_xwalk_ri_ref_attrib 
ON  vt_src_cd_val_xwalk.CONFRM_CDSET_ATTRIB_KEY = vt_xwalk_ri_ref_attrib.CDSET_ATTRIB_KEY
AND vt_src_cd_val_xwalk.SRC_CDSET_KEY 		    = vt_xwalk_ri_ref_attrib.REF_CDSET_KEY
AND vt_src_cd_val_xwalk.CDSET_UNQ_NM IN ('PCW_0000_SR_CS229a_SVC_TYPE_MJR_MNR_CD_XWALK','PCW_0000_SR_CS229b_SVC_TYPE_MJR_MNR_CD_XWALK','PCW_0000_SR_CS897_ATTRIBUTES_XWALK')
;

    """)
    return insert_src_cd_val_xwalk_stg_tbl


def insert_src_cd_val_xwalk_aud_tbl(common_config):
    insert_src_cd_val_xwalk_aud_tbl = ccw.Statement(statement=
                                                    """INSERT INTO """ +
                                                    common_config['ccw_aud'] + """.CCW_DATA_QUAL(PROJ_NM, TRGT_SCHEMA_NM,
                                TRGT_TBLNM,
                                TRGT_TBL_KEY,
                                TRGT_COLMN_NM,
                                CRET_TIMESTMP,
                                LOAD_CTL_KEY,
                                SRC_DATA_TXT,
                                ERR_MSG_DESC)

        SELECT	CAST('ECSM_REF' AS VARCHAR(20)),
        '""" + common_config['stg_dbname'] + """',
        'SRC_CD_VAL_XWALK',
         vt_src_cd_val_xwalk.TRGT_KEY,
        (
        CASE 1 
            WHEN (
        CASE 
            WHEN (CAST( vt_src_cd_val_xwalk.SRC_DOMAIN_NM AS VARCHAR(10)) = ' ') THEN 1 
            WHEN NOT (CAST( vt_src_cd_val_xwalk.SRC_DOMAIN_NM AS VARCHAR(10)) = ' ') THEN 0 
            ELSE NULL 
        END) THEN 'CHNL_SRC_CD'
            WHEN (
        CASE  WHEN (CAST( vt_src_cd_val_xwalk.TGT_SRC_DOMAIN_NM AS VARCHAR(10)) = ' ') THEN 1 
            WHEN NOT (CAST( vt_src_cd_val_xwalk.TGT_SRC_DOMAIN_NM AS VARCHAR(10)) = ' ') THEN 0 
            ELSE NULL 
        END) THEN 'CONFRM_CDSET_CHNL_SRC_CD' 
            WHEN (
        CASE 
            WHEN ( vt_src_cd_val_xwalk.CONFRM_CDSET_NM = ' ') THEN 1 
            WHEN NOT ( vt_src_cd_val_xwalk.CONFRM_CDSET_NM = ' ') THEN 0 
            ELSE NULL 
        END) THEN 'CONFRM_CDSET_NM' 
            WHEN (
        CASE 
            WHEN ( vt_src_cd_val_xwalk.CONFRM_CD_VAL_TXT = ' ') THEN 1 
            WHEN NOT ( vt_src_cd_val_xwalk.CONFRM_CD_VAL_TXT = ' ') THEN 0 
            ELSE NULL 
        END) THEN 'CONFRM_CD_VAL_TXT' 
            WHEN (
        CASE 
            WHEN ( vt_src_cd_val_xwalk.SRC_CDSET_NM = ' ') THEN 1 
            WHEN NOT ( vt_src_cd_val_xwalk.SRC_CDSET_NM = ' ') THEN 0 
            ELSE NULL 
        END) THEN 'SRC_CDSET_NM' 
            WHEN (
        CASE 
            WHEN ( vt_src_cd_val_xwalk.CD_VAL_TXT = ' ') THEN 1 
            WHEN NOT ( vt_src_cd_val_xwalk.CD_VAL_TXT = ' ') THEN 0 
            ELSE NULL 
        END) THEN 'SRC_CD_VAL_TXT' 
            WHEN (
        CASE 
            WHEN ( vt_src_cd_val_xwalk.XWALK_ROW_ID = ' ') THEN 1 
            WHEN NOT ( vt_src_cd_val_xwalk.XWALK_ROW_ID = ' ') THEN 0 
            ELSE NULL 
        END) THEN 'XWALK_ROW_ID' 
            WHEN (
        CASE 
            WHEN ( vt_src_cd_val_xwalk.CDSET_UNQ_NM = ' ') THEN 1 
            WHEN NOT ( vt_src_cd_val_xwalk.CDSET_UNQ_NM = ' ') THEN 0 
            ELSE NULL 
        END) THEN 'XWALK_UNQ_NM' 
            WHEN (
        CASE 
            WHEN ( vt_src_cd_val_xwalk.CONFRM_CDSET_KEY = ' ') THEN 1 
            WHEN NOT ( vt_src_cd_val_xwalk.CONFRM_CDSET_KEY = ' ') THEN 0 
            ELSE NULL 
        END) THEN 'CONFRM_CDSET_KEY' 
            WHEN (
        CASE 
            WHEN ( vt_src_cd_val_xwalk.SRC_CDSET_KEY = ' ') THEN 1 
            WHEN NOT ( vt_src_cd_val_xwalk.SRC_CDSET_KEY = ' ') THEN 0 
            ELSE NULL 
        END) THEN 'SRC_CDSET_KEY' 
            WHEN (
        CASE 
            WHEN (CAST((CAST( vt_src_cd_val_xwalk.XWALK_BEG_DT AS TIMESTAMP 
            FORMAT 'YYYY-MM-DD')) AS VARCHAR(64)) = '0001-01-01') THEN 1 
            WHEN NOT (CAST((CAST( vt_src_cd_val_xwalk.XWALK_BEG_DT AS TIMESTAMP 
            FORMAT 'YYYY-MM-DD')) AS VARCHAR(64)) = '0001-01-01') THEN 0 
            ELSE NULL 
        END) THEN 'XWALK_BEG_DT' 
            WHEN (
        CASE 
            WHEN (CAST((CAST( vt_src_cd_val_xwalk.XWALK_END_DT AS TIMESTAMP 
            FORMAT 'YYYY-MM-DD')) AS VARCHAR(64)) = '001-01-01') THEN 1 
            WHEN NOT (CAST((CAST( vt_src_cd_val_xwalk.XWALK_END_DT AS TIMESTAMP 
            FORMAT 'YYYY-MM-DD')) AS VARCHAR(64)) = '001-01-01') THEN 0 
            ELSE NULL 
        END) THEN 'XWALK_END_DT' 
        END),
        CURRENT_TIMESTAMP,
        CAST(vt_src_cd_val_xwalk.LOAD_CTL_KEY AS BIGINT),
        NULL,
        'NULL VALUE FOUND IN NOT NULL COLUMN' 
        FROM	 vt_src_cd_val_xwalk 
        WHERE	((
        CASE 
            WHEN (((((((((CAST( vt_src_cd_val_xwalk.SRC_DOMAIN_NM 
            AS VARCHAR(10)) = ' ')
            OR (CAST( vt_src_cd_val_xwalk.TGT_SRC_DOMAIN_NM 
            AS VARCHAR(10)) = ' ') 
            OR ( vt_src_cd_val_xwalk.CONFRM_CDSET_NM = ' ')) 
            OR ( vt_src_cd_val_xwalk.CONFRM_CD_VAL_TXT = ' ')) 
            OR ( vt_src_cd_val_xwalk.SRC_CDSET_NM = ' '))
            OR ( vt_src_cd_val_xwalk.CD_VAL_TXT = ' '))
            OR ( vt_src_cd_val_xwalk.XWALK_ROW_ID = ' '))
            OR ( vt_src_cd_val_xwalk.CDSET_UNQ_NM = ' ')) 
            OR ( vt_src_cd_val_xwalk.CONFRM_CDSET_KEY = ' ')) 
            OR ( vt_src_cd_val_xwalk.SRC_CDSET_KEY = ' ')) THEN 'Y'
            ELSE 'N' 
        END) = 'Y')""")
    return insert_src_cd_val_xwalk_aud_tbl


def post_sql_execution(common_config):
    post_sql_execution_st = ccw.Statement(
        statement="""UPDATE """ + common_config[
                                           'stg_dbname'] + """.SRC_CD_VAL_XWALK 
    SET CHK_SUM_TXT = HASH_MD5 (COALESCE( XWALK_ROW_ID,
    ' ')||'_'||COALESCE( XWALK_UNQ_NM,
    ' '));""") 
    return post_sql_execution_st


def main(common_config, audit_config, section):
    current_dir = abspath(dirname(__file__))
    current_dir = current_dir.replace("ecsm/etl_lz_stg/",
                                      "base/etl_stg_base/")
    common_config_filepath = join(current_dir,
                                  '../common_lib/config_file.ini')
    db_connect = ccw.DatabaseConnection.from_config_file(
        common_config_filepath, section=section)

    try:
        # create a session
        db_connect.create_session()

        # create sql execution strings
        trunc_src_cd_val_xwlk = trunc_src_cd_val_xwalk(common_config)
        vt_src_cd_val_xwlk = vt_src_cd_val_xwalk(common_config)
        vt_xwalk_ri_ref_attrb=vt_xwalk_ri_ref_attrib(common_config)
        insert_src_cd_val_xwlk_stg_tbl = insert_src_cd_val_xwalk_stg_tbl(
            common_config)
        insert_src_cd_val_xwlk_aud_tbl = insert_src_cd_val_xwalk_aud_tbl(
            common_config)
        post_sql_exec = post_sql_execution(common_config)

        # execute sql strings
        trunc_src_cd_val_xwlk.execute(db_connect)
        print('truncated table')

        vt_src_cd_val_xwlk.execute(db_connect)
        print('created volatile table')

        vt_xwalk_ri_ref_attrb.execute(db_connect)
        print('created attrib volatile table')

        insert_src_cd_val_xwlk_stg_tbl.execute(db_connect)
        print('inserted src_cd_val_xwalk stage_table')

        insert_src_cd_val_xwlk_aud_tbl.execute(db_connect)
        print('inserted table')

        post_sql_exec.execute(db_connect)
        print('executing post sql')

        print("_____________________________________________")
        print(" 'SRC_CD_VAL_XWALK' Table loaded successfully")
        print("---------------------------------------------")
    except Exception as e:
        print(e.message)
        print(traceback.format_exc())
        sys.exit(1)
    finally:
        db_connect.close_session()


if __name__ == '__main__':
    folder_name = sys.argv[1]
    script_name = sys.argv[2]
    section = sys.argv[3]
    layer = sys.argv[4]
    read_obj = ReadConfig(section, script_name, folder_name, layer)
    common_config = read_obj.get_common_config()
    audit_config = read_obj.get_audit_config()
    main(common_config, audit_config, section) 