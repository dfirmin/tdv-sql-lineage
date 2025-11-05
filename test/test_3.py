import sys
import os
import traceback
import ccw_etl_library as ccw

# appending python directory to read imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from read_config import ReadConfig


def vol_mult_val_sq(common_config):
    statement = """
    CREATE VOLATILE TABLE REF_MUL_VAL_SQ ( 
    REF_MULT_VAL_XWALK_KEY,
    REF_CD_VAL_KEY, 
    LOAD_CTL_KEY, 
    CURR_RCD_IND, 
    CHK_SUM_TXT, 
    CHNL_SRC_CD,
    CHNL_CD, 
    EFF_DT, 
    TERM_DT, 
    XWALK_UNQ_NM, 
    XWALK_ROW_ID, 
    SRC_TRGT_NM,
    CDSET_NM, 
    CD_VAL_TXT, 
    CD_VAL_UNQ_ID, 
    XWALK_BEG_DT, 
    XWALK_END_DT,
    TGT_REF_MULT_VAL_XWALK_KEY, 
    TGT_REF_CD_VAL_KEY, 
    TGT_CHK_SUM_TXT,
    TGT_EFF_DT, 
    TGT_XWALK_ROW_ID, 
    TGT_SRC_TRGT_NM, 
    TGT_CDSET_NM,
    TGT_CD_VAL_TXT, 
    TGT_CHNL_SRC_CD, 
    TGT_XWALK_BEG_DT, 
    TGT_XWALK_END_DT,
    INS_FLAG, 
    UPD_FLAG, 
    INS_EFF_DT, 
    UPD_END_DT) 
    AS 
    ( 
    SELECT	 
    STG_MULT_VAL.REF_MULT_VAL_XWALK_KEY,
    STG_MULT_VAL.REF_CD_VAL_KEY, 
    STG_MULT_VAL.LOAD_CTL_KEY, 
    CASE 
    WHEN	STG_MULT_VAL.TERM_DT=TO_DATE('9999-12-31','YYYY-MM-DD') THEN 'Y' 
    ELSE	'N' 
    END	AS CURR_RCD_IND, 
    STG_MULT_VAL.CHK_SUM_TXT, 
    STG_MULT_VAL.CHNL_SRC_CD,
    STG_MULT_VAL.CHNL_CD, 
    STG_MULT_VAL.EFF_DT,
    STG_MULT_VAL.TERM_DT,
    STG_MULT_VAL.XWALK_UNQ_NM,
    STG_MULT_VAL.XWALK_ROW_ID, 
    STG_MULT_VAL.SRC_TRGT_NM,
    STG_MULT_VAL.CDSET_NM,
    STG_MULT_VAL.CD_VAL_TXT,
    STG_MULT_VAL.CD_VAL_UNQ_ID,
    STG_MULT_VAL.XWALK_BEG_DT,
    STG_MULT_VAL.XWALK_END_DT,
    BASE_MULT_VAL.REF_MULT_VAL_XWALK_KEY,
    BASE_MULT_VAL.REF_CD_VAL_KEY,
    BASE_MULT_VAL.CHK_SUM_TXT,
    BASE_MULT_VAL.EFF_DT,
    BASE_MULT_VAL.XWALK_ROW_ID,
    BASE_MULT_VAL.SRC_TRGT_NM,
    BASE_MULT_VAL.CDSET_NM,
    BASE_MULT_VAL.CD_VAL_TXT,
    BASE_MULT_VAL.CHNL_SRC_CD,
    BASE_MULT_VAL.XWALK_BEG_DT,
    BASE_MULT_VAL.XWALK_END_DT,
    CASE	WHEN (BASE_MULT_VAL.REF_MULT_VAL_XWALK_KEY IS NOT NULL 
        AND	STG_MULT_VAL.CHK_SUM_TXT<>BASE_MULT_VAL.CHK_SUM_TXT 
        AND	BASE_MULT_VAL.EFF_DT <> CURRENT_DATE) 
        OR	(BASE_MULT_VAL.REF_MULT_VAL_XWALK_KEY IS NULL 
        AND	BASE_MULT_VAL_INACTIVE.REF_MULT_VAL_XWALK_KEY IS NULL)
        OR	(BASE_MULT_VAL.REF_MULT_VAL_XWALK_KEY IS NULL 
        AND	BASE_MULT_VAL_INACTIVE.REF_MULT_VAL_XWALK_KEY IS NOT NULL 
        AND	STG_MULT_VAL.CHK_SUM_TXT<>BASE_MULT_VAL_INACTIVE.CHK_SUM_TXT 
        AND	BASE_MULT_VAL_INACTIVE.EFF_DT <> CURRENT_DATE) 
    THEN 'I' 
    ELSE	'N' 
    END	AS INS_FLAG,
    CASE	WHEN (BASE_MULT_VAL.REF_MULT_VAL_XWALK_KEY IS NOT NULL 
        AND	STG_MULT_VAL.CHK_SUM_TXT<>BASE_MULT_VAL.CHK_SUM_TXT 
        AND	BASE_MULT_VAL.EFF_DT <> CURRENT_DATE)
        OR	(BASE_MULT_VAL.REF_MULT_VAL_XWALK_KEY IS NOT NULL 
        AND	STG_MULT_VAL.CHK_SUM_TXT=BASE_MULT_VAL.CHK_SUM_TXT 
        AND	STG_MULT_VAL.XWALK_END_DT <> BASE_MULT_VAL.XWALK_END_DT)
    THEN 'U' 
    ELSE	'N' 
    END	AS UPD_FLAG,
    CASE	WHEN BASE_MULT_VAL_INACTIVE.REF_MULT_VAL_XWALK_KEY IS NOT NULL THEN CURRENT_DATE 
    END	AS INS_EFF_DT,
    CURRENT_DATE - INTERVAL '1' DAY AS UPD_END_DT
    FROM	 
    (
    SEL	
        REF_MULT_VAL_XWALK_KEY,
        REF_CD_VAL_KEY, 
        LOAD_CTL_KEY, 
        CHK_SUM_TXT, 
        CHNL_SRC_CD,
        CHNL_CD, 
        XWALK_BEG_DT AS EFF_DT,
        COALESCE(MIN(XWALK_BEG_DT) OVER(PARTITION BY XWALK_ROW_ID,SRC_TRGT_NM,
            CDSET_NM,CD_VAL_TXT,
        CHNL_SRC_CD 
    ORDER	BY XWALK_BEG_DT ASC ROWS BETWEEN 1 FOLLOWING 
        AND	1 FOLLOWING)
        - INTERVAL '1' DAY ,TO_DATE('9999-12-31','YYYY-MM-DD')) AS TERM_DT,
        XWALK_UNQ_NM,
        XWALK_ROW_ID, 
        SRC_TRGT_NM,
        CDSET_NM,
        CD_VAL_TXT,
        CD_VAL_UNQ_ID,
        XWALK_BEG_DT,
        XWALK_END_DT
    FROM	""" + common_config['stg_dbname'] + """.REF_MULT_VAL_XWALK) STG_MULT_VAL
    LEFT JOIN """ + common_config['view_dbname'] + """.REF_MULT_VAL_XWALK BASE_MULT_VAL 
        ON	STG_MULT_VAL.REF_MULT_VAL_XWALK_KEY=BASE_MULT_VAL.REF_MULT_VAL_XWALK_KEY
        AND	BASE_MULT_VAL.CURR_RCD_IND='Y'
    LEFT JOIN (
    SELECT	REF_MULT_VAL_XWALK_KEY,REF_CD_VAL_KEY,XWALK_ROW_ID,SRC_TRGT_NM,
            CDSET_NM,CD_VAL_TXT,CHNL_SRC_CD,XWALK_BEG_DT,EFF_DT,CHK_SUM_TXT
    FROM	 """ + common_config['view_dbname'] + """.REF_MULT_VAL_XWALK BASE_MULT_VAL_D 
    WHERE	 BASE_MULT_VAL_D.CURR_RCD_IND='N'
    QUALIFY	ROW_NUMBER() OVER (PARTITION BY XWALK_ROW_ID,SRC_TRGT_NM,
            CDSET_NM,CD_VAL_TXT,CHNL_SRC_CD,XWALK_BEG_DT 
    ORDER	BY EFF_DT DESC)=1) BASE_MULT_VAL_INACTIVE
        ON	STG_MULT_VAL.REF_MULT_VAL_XWALK_KEY=BASE_MULT_VAL_INACTIVE.REF_MULT_VAL_XWALK_KEY )
            WITH DATA ON COMMIT PRESERVE ROWS;
    """
    return statement 

def vol_xwalk_upd():
    statement = """
    CREATE	VOLATILE TABLE VOL_XWALK_UPD (
    UPDT_TS, 
    LOAD_CTL_KEY,
    CURR_RCD_IND, 
    CHNL_SRC_CD, 
    EFF_DT, 
    TERM_DT, 
    XWALK_ROW_ID, 
    SRC_TRGT_NM,
    CDSET_NM, 
    CD_VAL_TXT, 
    XWALK_BEG_DT, 
    XWALK_END_DT) AS 
    (SELECT	CURRENT_TIMESTAMP,
            REF_MUL_VAL_SQ.LOAD_CTL_KEY, 
            CAST(CAST((
            CASE	1 
                WHEN	(
            CASE	WHEN ((NOT (REF_MUL_VAL_SQ.TGT_REF_MULT_VAL_XWALK_KEY IS NULL) 
                AND	(REF_MUL_VAL_SQ.TGT_CHK_SUM_TXT = REF_MUL_VAL_SQ.CHK_SUM_TXT)) 
                AND	(REF_MUL_VAL_SQ.XWALK_END_DT <> REF_MUL_VAL_SQ.TGT_XWALK_END_DT)) THEN 1 
                WHEN	NOT ((NOT (REF_MUL_VAL_SQ.TGT_REF_MULT_VAL_XWALK_KEY IS NULL) 
                AND	(REF_MUL_VAL_SQ.TGT_CHK_SUM_TXT = REF_MUL_VAL_SQ.CHK_SUM_TXT)) 
                AND	(REF_MUL_VAL_SQ.XWALK_END_DT <> REF_MUL_VAL_SQ.TGT_XWALK_END_DT)) THEN 0 
            ELSE	NULL 
            END	) THEN 'Y' 
            ELSE	'N' 
            END	) AS VARCHAR(10)) AS VARCHAR(1)), 
            REF_MUL_VAL_SQ.TGT_CHNL_SRC_CD,
            CAST(REF_MUL_VAL_SQ.TGT_EFF_DT AS date), 
            CAST(REF_MUL_VAL_SQ.UPD_END_DT AS date),
            REF_MUL_VAL_SQ.TGT_XWALK_ROW_ID, 
            REF_MUL_VAL_SQ.TGT_SRC_TRGT_NM,
            REF_MUL_VAL_SQ.TGT_CDSET_NM, 
            REF_MUL_VAL_SQ.TGT_CD_VAL_TXT,
            CAST(REF_MUL_VAL_SQ.TGT_XWALK_BEG_DT AS date),
            CAST(REF_MUL_VAL_SQ.XWALK_END_DT AS date) 
    FROM	REF_MUL_VAL_SQ 
    WHERE	(REF_MUL_VAL_SQ.UPD_FLAG = 'U') )
    WITH DATA ON COMMIT PRESERVE ROWS;
    """
    return statement


def upd_base_mult_val_xwalk(common_config):
    statement = """
    UPDATE	""" + common_config['base_dbname'] + """.REF_MULT_VAL_XWALK 
    FROM	VOL_XWALK_UPD 
    SET	UPDT_TS = VOL_XWALK_UPD.UPDT_TS, 
        LOAD_CTL_KEY = VOL_XWALK_UPD.LOAD_CTL_KEY,
        CURR_RCD_IND = VOL_XWALK_UPD.CURR_RCD_IND, 
        TERM_DT = VOL_XWALK_UPD.TERM_DT,
        XWALK_END_DT = VOL_XWALK_UPD.XWALK_END_DT 
    WHERE	(""" + common_config['base_dbname'] + """.REF_MULT_VAL_XWALK.CHNL_SRC_CD = VOL_XWALK_UPD.CHNL_SRC_CD 
        AND	""" + common_config['base_dbname'] + """.REF_MULT_VAL_XWALK.EFF_DT = VOL_XWALK_UPD.EFF_DT 
        AND	""" + common_config['base_dbname'] + """.REF_MULT_VAL_XWALK.XWALK_ROW_ID = VOL_XWALK_UPD.XWALK_ROW_ID 
        AND	""" + common_config['base_dbname'] + """.REF_MULT_VAL_XWALK.SRC_TRGT_NM = VOL_XWALK_UPD.SRC_TRGT_NM 
        AND	""" + common_config['base_dbname'] + """.REF_MULT_VAL_XWALK.CDSET_NM = VOL_XWALK_UPD.CDSET_NM 
        AND	""" + common_config['base_dbname'] + """.REF_MULT_VAL_XWALK.CD_VAL_TXT = VOL_XWALK_UPD.CD_VAL_TXT 
        AND	""" + common_config['base_dbname'] + """.REF_MULT_VAL_XWALK.XWALK_BEG_DT = VOL_XWALK_UPD.XWALK_BEG_DT); 

    """
    return statement


def ins_base_mult_val_xwalk(common_config):
    statement = """
    INSERT	INTO """ + common_config['base_dbname'] + """.REF_MULT_VAL_XWALK
    (
    REF_MULT_VAL_XWALK_KEY,
    REF_CD_VAL_KEY, 
    CRET_TS, 
    UPDT_TS, 
    LOAD_CTL_KEY, 
    CURR_RCD_IND,
    CHK_SUM_TXT, 
    CHNL_SRC_CD, 
    CHNL_CD, 
    EFF_DT, 
    TERM_DT, 
    XWALK_UNQ_NM,
    XWALK_ROW_ID, 
    SRC_TRGT_NM, 
    CDSET_NM, 
    CD_VAL_TXT, 
    CD_VAL_UNQ_ID,
    XWALK_BEG_DT, 
    XWALK_END_DT) 
    SELECT	REF_MUL_VAL_SQ.REF_MULT_VAL_XWALK_KEY, 
            REF_MUL_VAL_SQ.REF_CD_VAL_KEY,
            CAST(CAST(CURRENT_TIMESTAMP AS TIMESTAMP FORMAT 'Y4-MM-DDBHH:MI:SS') AS TIMESTAMP),
            CAST(CAST('9999-12-31' AS TIMESTAMP FORMAT 'YYYY/MM/DD') AS timestamp),
            REF_MUL_VAL_SQ.LOAD_CTL_KEY, 
            CAST(REF_MUL_VAL_SQ.CURR_RCD_IND AS VARCHAR(1)),
            REF_MUL_VAL_SQ.CHK_SUM_TXT, 
            REF_MUL_VAL_SQ.CHNL_SRC_CD,
            REF_MUL_VAL_SQ.CHNL_CD, 
            CAST(( 
            CASE	WHEN NOT (REF_MUL_VAL_SQ.INS_EFF_DT IS NULL) THEN REF_MUL_VAL_SQ.INS_EFF_DT 
            ELSE	REF_MUL_VAL_SQ.EFF_DT 
            END	) AS date), 
            CAST(REF_MUL_VAL_SQ.TERM_DT AS date),
            REF_MUL_VAL_SQ.XWALK_UNQ_NM, 
            REF_MUL_VAL_SQ.XWALK_ROW_ID,
            REF_MUL_VAL_SQ.SRC_TRGT_NM, 
            REF_MUL_VAL_SQ.CDSET_NM,
            REF_MUL_VAL_SQ.CD_VAL_TXT, 
            REF_MUL_VAL_SQ.CD_VAL_UNQ_ID,
            CAST(REF_MUL_VAL_SQ.XWALK_BEG_DT AS date), 
            CAST(REF_MUL_VAL_SQ.XWALK_END_DT AS date) 
    FROM	REF_MUL_VAL_SQ 
    WHERE	(REF_MUL_VAL_SQ.INS_FLAG = 'I');
    """
    return statement


def coll_stats_ref_mult_val_xwalk(common_config):
    statement = """        
    COLLECT	STATS COLUMN (REF_MULT_VAL_XWALK_KEY),
                  COLUMN (REF_CD_VAL_KEY),
                  COLUMN (XWALK_ROW_ID),
                  COLUMN (SRC_TRGT_NM),
                  COLUMN (CDSET_NM),
                  COLUMN (CD_VAL_TXT),
                  COLUMN (CHNL_SRC_CD),
                  COLUMN (XWALK_BEG_DT)
        ON	""" + common_config['base_dbname'] + """.REF_MULT_VAL_XWALK ;
         """
    return statement 

def upd_ref_mult_val_xwalk(common_config):
    statement = """
    UPD	""" + common_config['base_dbname'] + """.REF_MULT_VAL_XWALK 
    SET	CURR_RCD_IND = 'N' 
    where	(XWALK_ROW_ID,
            SRC_TRGT_NM,
            CDSET_NM,
            CD_VAL_TXT,
            CHNL_SRC_CD,
            XWALK_BEG_DT) not in ( 
    SEL	* 
    FROM	(
    sel	XWALK_ROW_ID,
        SRC_TRGT_NM,
        CDSET_NM,
        CD_VAL_TXT,
        CHNL_SRC_CD,
        XWALK_BEG_DT 
    from	""" + common_config['base_dbname'] + """.REF_MULT_VAL_XWALK
    QUALIFY	ROW_NUMBER() OVER (PARTITION BY XWALK_ROW_ID,SRC_TRGT_NM,
            CDSET_NM,CD_VAL_TXT,CHNL_SRC_CD 
    ORDER	BY XWALK_BEG_DT DESC) = 1)A);

    """
    return statement


def main(common_config, env):
    """
    main method that loads CHNL_SRC_SYS
    :param common_config    :   common configuration dict
    :param env          :   Configuration section parameter
    :return                 :   nothing
    """
    current_dir = os.path.abspath(os.path.dirname(__file__))
    common_config_filepath = os.path.join(current_dir,
                                          '../common_lib/config_file.ini')
    db_connect = ccw.DatabaseConnection.from_config_file(
        common_config_filepath, section=env)
    
    # Turn off autocommit to ensure ETL is done in a single transaction
    db_connect.db_config.session_parameters['autoCommit'] = False

    # create your session
    db_connect.create_session()
    try:
        ccw.Statement(vol_mult_val_sq(
            common_config)).execute(db_connect)
        
        # commit needed after any DDL (including volatile tables)
        db_connect.session.commit()

        ccw.Statement(vol_xwalk_upd()).execute(db_connect)

        # commit needed after any DDL (including volatile tables)
        db_connect.session.commit()

        ccw.Statement(upd_base_mult_val_xwalk(
            common_config)).execute(db_connect)
        ccw.Statement(ins_base_mult_val_xwalk(
            common_config)).execute(db_connect)
        ccw.Statement(coll_stats_ref_mult_val_xwalk(
            common_config)).execute(db_connect)
        
        # commit needed after any DDL (including volatile tables)
        db_connect.session.commit()

        ccw.Statement(upd_ref_mult_val_xwalk(
            common_config)).execute(db_connect)
        
        # commit DML changes
        db_connect.session.commit()

        print("____________________________________________________")
        print(" BASE 'REF_MULT_VAL_XWALK' Table loaded successfully")
        print("----------------------------------------------------")
    except Exception as e:
        print((e.message))
        print((traceback.format_exc()))
        sys.exit(1)
    finally:
        db_connect.close_session()


if __name__ == '__main__':
    foldername = sys.argv[1]
    scriptname = sys.argv[2]
    section = sys.argv[3]
    layer = sys.argv[4]
    read_obj = ReadConfig(section, scriptname, foldername, layer)
    commonconfig = read_obj.get_common_config()
    auditconfig = read_obj.get_audit_config()
    main(commonconfig, section) 