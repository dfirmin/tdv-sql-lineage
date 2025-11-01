import sys
import traceback
from os.path import dirname, join, abspath
import ccw_etl_library as ccw

# appending python directory to read imports
sys.path.append(dirname(dirname(__file__)))
from read_config import ReadConfig


def vt_base_src_cd_xwalk(common_config):
    vt_base_src_cd_xwalk = ccw.Statement(
        statement="""CREATE VOLATILE TABLE VT_BASE_SRC_CD_XWALK  (
                         CONFRM_CD_VAL_KEY,
                         SRC_CD_VAL_KEY,
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
                         TGT_CONFRM_CD_VAL_KEY,
                         TGT_SRC_CD_VAL_KEY,
                         TGT_CHK_SUM_TXT,
                         TGT_XWALK_BEG_DT,
                         INS_FLAG,
                         UPD_FLAG,
                         UPD_END_DT,
                         EFF_DT,
                         TERM_DT,
                         CHNL_CD) AS (
                    SELECT
                             STG_XWALK_I1.CONFRM_CD_VAL_KEY, 
                             STG_XWALK_I1.SRC_CD_VAL_KEY, 
                             STG_XWALK_I1.CHNL_SRC_CD,
                             STG_XWALK_I1.CONFRM_CDSET_CHNL_SRC_CD, 
                             CASE 
                                     WHEN STG_XWALK_I1.XWALK_END_DT = To_Date('9999-12-31',
                'YYYY-MM-DD') THEN  'Y' 
                                     ELSE 'N' 
                                 end AS CURR_IND ,

                             STG_XWALK_I1.CHK_SUM_TXT, 
                             STG_XWALK_I1.LOAD_CTL_KEY, 
                             STG_XWALK_I1.CONFRM_CDSET_NM, 
                             STG_XWALK_I1.CONFRM_CD_VAL_TXT, 
                             STG_XWALK_I1.SRC_CDSET_NM, 
                             STG_XWALK_I1.SRC_CD_VAL_TXT, 
                             STG_XWALK_I1.XWALK_ROW_ID, 
                             STG_XWALK_I1.XWALK_UNQ_NM, 
                             STG_XWALK_I1.CONFRM_CDSET_KEY, 
                             STG_XWALK_I1.SRC_CDSET_KEY, 
                             STG_XWALK_I1.CONFRM_CDSET_UNQ_ID,
                             STG_XWALK_I1.SRC_CDSET_UNQ_ID,
                             STG_XWALK_I1.XWALK_BEG_DT, 
                             STG_XWALK_I1.XWALK_END_DT, 
                             REF_CLOSEST_DAY.CONFRM_CD_VAL_KEY AS TGT_CONFRM_CD_VAL_KEY,
                             REF_CLOSEST_DAY.SRC_CD_VAL_KEY AS TGT_SRC_CD_VAL_KEY,

                             REF_CLOSEST_DAY.CHK_SUM_TXT AS TGT_CHK_SUM_TXT,
                             Coalesce(REF_CLOSEST_DAY.MIN_XWALK_BEG_DT,
                To_Date('0001-01-01',
                                 'YYYY-MM-DD')) AS TGT_XWALK_BEG_DT,
                             CASE	
                                     WHEN (REF_CLOSEST_DAY.SRC_CD_VAL_KEY IS NULL 
                             AND REF_XWALK_INS.SRC_CD_VAL_KEY IS NULL) 
                                     OR ( REF_CLOSEST_DAY.SRC_CD_VAL_KEY IS NOT NULL 
                                          AND REF_CLOSEST_DAY.MAX_XWALK_BEG_DT<STG_XWALK_I1.XWALK_BEG_DT )
                                     OR ( REF_CLOSEST_DAY.SRC_CD_VAL_KEY IS NULL 
                             AND REF_XWALK_INS.SRC_CD_VAL_KEY IS NOT NULL 
                             AND REF_XWALK_INS.XWALK_BEG_DT<STG_XWALK_I1.XWALK_BEG_DT )
                                     THEN 'I'
                                     ELSE 'N'	
                                 END AS INS_FLAG,
                             CASE
                                     WHEN REF_CLOSEST_DAY.SRC_CD_VAL_KEY IS NOT NULL 
                                     AND REF_CLOSEST_DAY.DIFF_DAYS=Cast(STG_XWALK_I1.XWALK_BEG_DT AS INTEGER FORMAT '99999999') - Cast(REF_CLOSEST_DAY.MIN_XWALK_BEG_DT AS INTEGER FORMAT '99999999')
                                     AND 
                                     (
                                         (

                                         REF_CLOSEST_DAY.MIN_XWALK_BEG_DT<STG_XWALK_I1.XWALK_BEG_DT
                                         )
                                         OR
                                         (

                                         REF_CLOSEST_DAY.MIN_XWALK_BEG_DT=STG_XWALK_I1.XWALK_BEG_DT
                                         AND REF_CLOSEST_DAY.XWALK_END_DT>STG_XWALK_I1.XWALK_END_DT
                                         ) 
                                                                             )
                                     THEN 'U'
                                     ELSE 'N'	
                                 END AS UPD_FLAG,
                             CASE 
                                     WHEN REF_CLOSEST_DAY.MIN_XWALK_BEG_DT<STG_XWALK_I1.XWALK_BEG_DT THEN STG_XWALK_I1.XWALK_BEG_DT  - INTERVAL '1' DAY
                                 ELSE STG_XWALK_I1.XWALK_END_DT  
                                 end AS UPD_END_DT,
                                 STG_XWALK_I1.EFF_DT,
                                 STG_XWALK_I1.TERM_DT,
                                 STG_XWALK_I1.CHNL_CD
                    FROM	""" + common_config['stg_dbname'] + """.SRC_CD_VAL_XWALK STG_XWALK_I1

                    LEFT JOIN 
                    (
                        SELECT	STG_i.SRC_CD_VAL_KEY, 
                                Min (Cast(STG_i.XWALK_BEG_DT AS INTEGER FORMAT '99999999') - Cast(REF_i.XWALK_BEG_DT AS INTEGER FORMAT '99999999')) AS DIFF_DAYS,
                                Min(REF_MIN_DT_CHK_SUM.MIN_DT) AS MIN_XWALK_BEG_DT,
                                Max(REF_MIN_DT_CHK_SUM.MAX_DT) AS MAX_XWALK_BEG_DT,
                            Max(REF_i.XWALK_END_DT) XWALK_END_DT,
                            Min(REF_i.CHK_SUM_TXT) CHK_SUM_TXT
                            ,STG_i.CONFRM_CD_VAL_KEY
                            FROM	""" + common_config['view_dbname'] + """
                                .SRC_CD_VAL_XWALK REF_i
                            JOIN """ + common_config['stg_dbname'] + """
                                    .SRC_CD_VAL_XWALK STG_i
                        ON STG_i.SRC_CD_VAL_KEY(CaseSpecific)=REF_i.SRC_CD_VAL_KEY(CaseSpecific)
                        AND STG_i.CONFRM_CD_VAL_KEY(CaseSpecific)=REF_i.CONFRM_CD_VAL_KEY(CaseSpecific)
                        AND REF_i.CURR_RCD_IND='Y'
                        AND STG_i.XWALK_BEG_DT >= REF_i.XWALK_BEG_DT
                        AND STG_i.XWALK_BEG_DT < STG_i.XWALK_END_DT
                        JOIN (
                            SELECT	SRC_CD_VAL_KEY,Min(XWALK_BEG_DT) AS MIN_DT,
                    Max(XWALK_BEG_DT) AS MAX_DT  ,
                             CONFRM_CD_VAL_KEY
                                     FROM	""" + common_config[
            'view_dbname'] + """.SRC_CD_VAL_XWALK  
                                                                WHERE	CURR_RCD_IND = 'Y' 
                                                                GROUP BY SRC_CD_VAL_KEY ,
                    CONFRM_CD_VAL_KEY) AS REF_MIN_DT_CHK_SUM
                                            ON REF_i.SRC_CD_VAL_KEY = REF_MIN_DT_CHK_SUM.SRC_CD_VAL_KEY
                                            AND REF_MIN_DT_CHK_SUM.MIN_DT = REF_i.XWALK_BEG_DT
                                            AND REF_i.CONFRM_CD_VAL_KEY = REF_MIN_DT_CHK_SUM.CONFRM_CD_VAL_KEY
                                            GROUP BY STG_i.SRC_CD_VAL_KEY  ,
                STG_i.CONFRM_CD_VAL_KEY) REF_CLOSEST_DAY
                                    ON REF_CLOSEST_DAY.SRC_CD_VAL_KEY=STG_XWALK_I1.SRC_CD_VAL_KEY
                                    AND REF_CLOSEST_DAY.CONFRM_CD_VAL_KEY(CaseSpecific)=STG_XWALK_I1.CONFRM_CD_VAL_KEY(CaseSpecific)

                                    LEFT JOIN 
                                    (
                                        SELECT	SRC_CD_VAL_KEY, Max(XWALK_BEG_DT) AS XWALK_BEG_DT 
                                                ,CONFRM_CD_VAL_KEY
                                                FROM	""" + common_config[
                      'view_dbname'] + """.SRC_CD_VAL_XWALK 
                                                WHERE	CURR_RCD_IND='N' 
                                                GROUP BY SRC_CD_VAL_KEY ,
                CONFRM_CD_VAL_KEY) REF_XWALK_INS
                                    ON STG_XWALK_I1.SRC_CD_VAL_KEY(CaseSpecific)=REF_XWALK_INS.SRC_CD_VAL_KEY(CaseSpecific)
                                    AND STG_XWALK_I1.CONFRM_CD_VAL_KEY(CaseSpecific)=REF_XWALK_INS.CONFRM_CD_VAL_KEY(CaseSpecific)
                                    WHERE	STG_XWALK_I1.XWALK_BEG_DT<STG_XWALK_I1.XWALK_END_DT )
                                WITH DATA  
                PRIMARY INDEX ( CONFRM_CD_VAL_KEY ,
                        SRC_CD_VAL_KEY )
                                                ON 
                COMMIT PRESERVE ROWS;"""
    )
    return vt_base_src_cd_xwalk


def cvt_base_src_cd_xwalk_u(common_config):
    vt_base_src_cd_xwalk_u = ccw.Statement(
        statement="""CREATE VOLATILE TABLE VT_BASE_SRC_CD_XWALK_U
                        (CONFRM_CD_VAL_KEY,
                         SRC_CD_VAL_KEY,
                         UPDT_TS,
                         CURR_RCD_IND,
                         LOAD_CTL_KEY,
                         XWALK_BEG_DT,
                         XWALK_END_DT) AS 
                    (
                     SELECT	VT_BASE_SRC_CD_XWALK.TGT_CONFRM_CD_VAL_KEY,
                             VT_BASE_SRC_CD_XWALK.SRC_CD_VAL_KEY,
                             CURRENT_TIMESTAMP,
                             Cast(Cast('N' AS VARCHAR(2)) AS VARCHAR(1)),
                             VT_BASE_SRC_CD_XWALK.LOAD_CTL_KEY,
                             Cast(VT_BASE_SRC_CD_XWALK.TGT_XWALK_BEG_DT AS 
                              DATE),
                             Cast(VT_BASE_SRC_CD_XWALK.UPD_END_DT AS DATE) 
                     FROM	VT_BASE_SRC_CD_XWALK 
                     WHERE	VT_BASE_SRC_CD_XWALK.UPD_FLAG = 'U' )
                     WITH DATA PRIMARY INDEX ( CONFRM_CD_VAL_KEY ,
                     SRC_CD_VAL_KEY )
                     ON COMMIT PRESERVE ROWS;"""
    )
    return vt_base_src_cd_xwalk_u


def upd_base_src_cd_xwalk_u(common_config):
    upd_base_src_cd_xwalk_u = ccw.Statement(
        statement="""UPDATE """ + common_config['base_dbname'] + """.SRC_CD_VAL_XWALK 
                           FROM	VT_BASE_SRC_CD_XWALK_U
                    SET UPDT_TS = VT_BASE_SRC_CD_XWALK_U.UPDT_TS,
                            CURR_RCD_IND = VT_BASE_SRC_CD_XWALK_U.CURR_RCD_IND,
                            LOAD_CTL_KEY = VT_BASE_SRC_CD_XWALK_U.LOAD_CTL_KEY,
                            XWALK_END_DT = VT_BASE_SRC_CD_XWALK_U.XWALK_END_DT
                    WHERE	(""" + common_config['base_dbname'] + """
                            .SRC_CD_VAL_XWALK.CONFRM_CD_VAL_KEY = VT_BASE_SRC_CD_XWALK_U.CONFRM_CD_VAL_KEY
                        AND """ + common_config['base_dbname'] + """
                            .SRC_CD_VAL_XWALK.SRC_CD_VAL_KEY = VT_BASE_SRC_CD_XWALK_U.SRC_CD_VAL_KEY
                        AND """ + common_config['base_dbname'] + """
                            .SRC_CD_VAL_XWALK.XWALK_BEG_DT = VT_BASE_SRC_CD_XWALK_U.XWALK_BEG_DT);"""
    )
    return upd_base_src_cd_xwalk_u


def ins_base_src_cd_xwalk(common_config):
    ins_base_src_cd_xwalk = ccw.Statement(
        statement="""INSERT INTO """ + common_config['base_dbname'] +
                  """.SRC_CD_VAL_XWALK(CONFRM_CD_VAL_KEY,
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
                    SELECT	VT_BASE_SRC_CD_XWALK.CONFRM_CD_VAL_KEY,
                            VT_BASE_SRC_CD_XWALK.SRC_CD_VAL_KEY,
                            CURRENT_TIMESTAMP,
                            Cast(Cast('9999/12/31' AS TIMESTAMP FORMAT 'YYYY/MM/DD') AS TIMESTAMP),
                            VT_BASE_SRC_CD_XWALK.CHNL_SRC_CD,
                            VT_BASE_SRC_CD_XWALK.CONFRM_CDSET_CHNL_SRC_CD,
                            VT_BASE_SRC_CD_XWALK.CURR_RCD_IND,
                            VT_BASE_SRC_CD_XWALK.CHK_SUM_TXT,
                            VT_BASE_SRC_CD_XWALK.LOAD_CTL_KEY,
                            VT_BASE_SRC_CD_XWALK.CONFRM_CDSET_NM,
                            VT_BASE_SRC_CD_XWALK.CONFRM_CD_VAL_TXT,
                            VT_BASE_SRC_CD_XWALK.SRC_CDSET_NM,
                            VT_BASE_SRC_CD_XWALK.SRC_CD_VAL_TXT,
                            VT_BASE_SRC_CD_XWALK.XWALK_ROW_ID,
                            VT_BASE_SRC_CD_XWALK.XWALK_UNQ_NM,
                            VT_BASE_SRC_CD_XWALK.CONFRM_CDSET_KEY,
                            VT_BASE_SRC_CD_XWALK.SRC_CDSET_KEY,
                            VT_BASE_SRC_CD_XWALK.CONFRM_CDSET_UNQ_ID,
                            VT_BASE_SRC_CD_XWALK.SRC_CDSET_UNQ_ID,
                            Cast(VT_BASE_SRC_CD_XWALK.XWALK_BEG_DT AS DATE),
                            Cast(VT_BASE_SRC_CD_XWALK.XWALK_END_DT AS DATE),
                            Cast(VT_BASE_SRC_CD_XWALK.EFF_DT AS DATE),
                            Cast(VT_BASE_SRC_CD_XWALK.TERM_DT AS DATE),
                            VT_BASE_SRC_CD_XWALK.CHNL_CD 
                    FROM	VT_BASE_SRC_CD_XWALK 
                    WHERE	(VT_BASE_SRC_CD_XWALK.INS_FLAG = 'I') ;""")
    return ins_base_src_cd_xwalk


def upd_base_src_cd_xwalk_one(common_config):
    upd_base_src_cd_xwalk_one = ccw.Statement(
        statement="""UPDATE BASE
                    FROM """ + common_config['stg_dbname'] + """.SRC_CD_VAL_XWALK STG,
                    """ + common_config['base_dbname'] + """.SRC_CD_VAL_XWALK BASE
                    SET XWALK_END_DT = STG.XWALK_END_DT
                    WHERE STG.SRC_CD_VAL_KEY = BASE.SRC_CD_VAL_KEY
                        AND STG.CONFRM_CD_VAL_KEY = BASE.CONFRM_CD_VAL_KEY
                        AND STG.CHK_SUM_TXT = BASE.CHK_SUM_TXT
                        AND STG.XWALK_BEG_DT = BASE.XWALK_BEG_DT
                        AND BASE.XWALK_END_DT = '9999-12-31'
                        AND BASE.XWALK_END_DT <>STG.XWALK_END_DT
                        AND BASE.CURR_RCD_IND='N';""")
    return upd_base_src_cd_xwalk_one


def upd_base_src_cd_xwalk_two(common_config):
    upd_base_src_cd_xwalk_two = ccw.Statement(
        statement="""UPDATE """ + common_config['base_dbname'] + """.SRC_CD_VAL_XWALK BASE_XWALK
                    SET CURR_RCD_IND='Y',TERM_DT='9999-12-31'
                    WHERE (BASE_XWALK.CURR_RCD_IND = 'N'
                        OR BASE_XWALK.TERM_DT<>'9999-12-31' )
                        AND EXISTS
                    (
                        SELECT 1
                        FROM
                        (
                            SELECT  XWALK.XWALK_UNQ_NM,XWALK.CHNL_SRC_CD,XWALK.SRC_CDSET_NM,
                            XWALK.SRC_CD_VAL_TXT, 
                                                       XWALK.CONFRM_CDSET_NM,
                            XWALK.CONFRM_CD_VAL_TXT,
                            XWALK.XWALK_BEG_DT,
                            XWALK.EFF_DT
                            FROM """ + common_config['view_dbname'] + """.SRC_CD_VAL_XWALK XWALK
                            WHERE EXISTS (
                                            SELECT 1
                        FROM """ + common_config['stg_dbname'] + """.SRC_CD_VAL_XWALK STG_XWALK
                                            WHERE XWALK.CHNL_SRC_CD= STG_XWALK.CHNL_SRC_CD
                                            AND XWALK.SRC_CDSET_NM= STG_XWALK.SRC_CDSET_NM
                                            AND XWALK.SRC_CD_VAL_TXT= STG_XWALK.SRC_CD_VAL_TXT
                                            AND XWALK.CONFRM_CDSET_NM= STG_XWALK.CONFRM_CDSET_NM
                                        )
                            QUALIFY Row_Number() Over (
                        PARTITION BY XWALK.XWALK_UNQ_NM,
                                XWALK.CHNL_SRC_CD,
                                XWALK.SRC_CDSET_NM,
                                XWALK.SRC_CD_VAL_TXT,
                                XWALK.CONFRM_CDSET_NM
                        ORDER BY XWALK.XWALK_BEG_DT DESC,
                                XWALK.EFF_DT DESC,
                                XWALK.CONFRM_CD_VAL_TXT) = 1
                        ) A
                        WHERE BASE_XWALK.XWALK_UNQ_NM= A.XWALK_UNQ_NM
                        AND BASE_XWALK.CHNL_SRC_CD= A.CHNL_SRC_CD
                        AND BASE_XWALK.SRC_CDSET_NM= A.SRC_CDSET_NM
                        AND BASE_XWALK.SRC_CD_VAL_TXT= A.SRC_CD_VAL_TXT
                        AND BASE_XWALK.CONFRM_CDSET_NM= A.CONFRM_CDSET_NM
                        AND BASE_XWALK.CONFRM_CD_VAL_TXT= A.CONFRM_CD_VAL_TXT
                        AND BASE_XWALK.XWALK_BEG_DT=A.XWALK_BEG_DT
                        AND BASE_XWALK.EFF_DT=A.EFF_DT
                    );""")
    return upd_base_src_cd_xwalk_two


def upd_base_src_cd_xwalk_three(common_config):
    """ CCW_BASE_DEV - common_config['base_dbname'] """
    upd_base_src_cd_xwalk_three = ccw.Statement(
        statement="""UPDATE """ + common_config['base_dbname'] + """.SRC_CD_VAL_XWALK BASE_XWALK
                SET CURR_RCD_IND='N',TERM_DT=Current_Date
                WHERE (CURR_RCD_IND='Y'
                    OR TERM_DT='9999-12-31')
                    AND EXISTS	(
                                    SELECT 1
                    FROM """ + common_config['stg_dbname'] + """.SRC_CD_VAL_XWALK STG_XWLK
                                    WHERE BASE_XWALK.XWALK_UNQ_NM= STG_XWLK.XWALK_UNQ_NM
                                    AND BASE_XWALK.CHNL_SRC_CD= STG_XWLK.CHNL_SRC_CD
                                    AND BASE_XWALK.SRC_CDSET_NM= STG_XWLK.SRC_CDSET_NM
                                    AND BASE_XWALK.SRC_CD_VAL_TXT= STG_XWLK.SRC_CD_VAL_TXT
                                    AND BASE_XWALK.CONFRM_CDSET_NM= STG_XWLK.CONFRM_CDSET_NM
                                )
                AND (BASE_XWALK.XWALK_UNQ_NM,BASE_XWALK.CHNL_SRC_CD,BASE_XWALK.SRC_CDSET_NM,
                    BASE_XWALK.SRC_CD_VAL_TXT,
                    BASE_XWALK.CONFRM_CDSET_NM,
                    BASE_XWALK.CONFRM_CD_VAL_TXT,
                    BASE_XWALK.XWALK_BEG_DT,
                    BASE_XWALK.EFF_DT ) NOT IN
                (
                    SELECT XWALK_UNQ_NM,CHNL_SRC_CD,SRC_CDSET_NM,SRC_CD_VAL_TXT,CONFRM_CDSET_NM,
                        CONFRM_CD_VAL_TXT,
                        XWALK_BEG_DT,
                        EFF_DT
                    FROM
                    (
                        SELECT  XWALK.XWALK_UNQ_NM,XWALK.CHNL_SRC_CD,XWALK.SRC_CDSET_NM,
                        XWALK.SRC_CD_VAL_TXT,
                        XWALK.CONFRM_CDSET_NM,
                        XWALK.CONFRM_CD_VAL_TXT,
                        XWALK.XWALK_BEG_DT,
                        XWALK.EFF_DT
                        FROM """ + common_config['view_dbname'] + """.SRC_CD_VAL_XWALK XWALK
                        WHERE  EXISTS (
                                        SELECT 1
                    FROM """ + common_config['stg_dbname'] + """.SRC_CD_VAL_XWALK STG_XWALK
                                        WHERE XWALK.XWALK_UNQ_NM= STG_XWALK.XWALK_UNQ_NM
                                        AND XWALK.CHNL_SRC_CD= STG_XWALK.CHNL_SRC_CD
                                        AND XWALK.SRC_CDSET_NM= STG_XWALK.SRC_CDSET_NM
                                        AND XWALK.SRC_CD_VAL_TXT= STG_XWALK.SRC_CD_VAL_TXT
                                        AND XWALK.CONFRM_CDSET_NM= STG_XWALK.CONFRM_CDSET_NM
                                    )
                        QUALIFY Row_Number() Over (
                PARTITION BY XWALK.XWALK_UNQ_NM,
                        XWALK.CHNL_SRC_CD,
                        XWALK.SRC_CDSET_NM,
                        XWALK.SRC_CD_VAL_TXT,
                        XWALK.CONFRM_CDSET_NM
                ORDER BY XWALK.XWALK_BEG_DT DESC,
                        XWALK.EFF_DT DESC,
                        XWALK.CONFRM_CD_VAL_TXT) = 1
                    ) A
                );""")
    return upd_base_src_cd_xwalk_three


def collect_stats(common_config):
    collect_stats = ccw.Statement(
        statement=
        """COLLECT STATS    COLUMN (CONFRM_CD_VAL_KEY),
                            COLUMN (SRC_CD_VAL_KEY),
                            COLUMN (CHNL_SRC_CD), 
                                                       COLUMN (CONFRM_CDSET_NM),
                            COLUMN (CONFRM_CD_VAL_TXT),
                            COLUMN (XWALK_BEG_DT),
                            COLUMN (EFF_DT),
                            COLUMN (SRC_CDSET_NM),
                            COLUMN (SRC_CD_VAL_TXT)
        ON """ + common_config['base_dbname'] + """.SRC_CD_VAL_XWALK;""")
    return collect_stats


def main(common_config, audit_config, section):
    current_dir = abspath(dirname(__file__))
    common_config_filepath = join(current_dir,
                                  '../common_lib/config_file.ini')
    db_connect = ccw.DatabaseConnection.from_config_file(
        common_config_filepath, section=section)
    
    # Turn off autocommit to ensure ETL is done in a single transaction
    db_connect.db_config.session_parameters['autoCommit'] = False

    try:
        # create a session
        db_connect.create_session()

        # create sql execution strings
        vt_base_src_cd_xwlk = vt_base_src_cd_xwalk(common_config)
        cvt_base_src_cd_xwlk_u = cvt_base_src_cd_xwalk_u(common_config)
        upd_base_src_cd_xwlk_u = upd_base_src_cd_xwalk_u(common_config)
        ins_base_src_cd_xwlk = ins_base_src_cd_xwalk(common_config)
        upd_base_src_cd_xwlk_one = upd_base_src_cd_xwalk_one(common_config)
        upd_base_src_cd_xwlk_two = upd_base_src_cd_xwalk_two(common_config)
        upd_base_src_cd_xwlk_three = upd_base_src_cd_xwalk_three(common_config)
        collects_stat = collect_stats(common_config)

        # execute sql strings
        vt_base_src_cd_xwlk.execute(db_connect)

        # commit needed after any DDL (including volatile tables)
        db_connect.session.commit()

        cvt_base_src_cd_xwlk_u.execute(db_connect)

        # commit needed after any DDL (including volatile tables)
        db_connect.session.commit()

        upd_base_src_cd_xwlk_u.execute(db_connect)
        ins_base_src_cd_xwlk.execute(db_connect)
        upd_base_src_cd_xwlk_one.execute(db_connect)
        upd_base_src_cd_xwlk_two.execute(db_connect)
        upd_base_src_cd_xwlk_three.execute(db_connect)
        collects_stat.execute(db_connect)
        
        # commit DML changes
        db_connect.session.commit()

        print("_____________________________________________")
        print(" 'SRC_CD_VAL_XWALK' Table loaded successfully")
        print("---------------------------------------------")

    except Exception as e:
        print((e.message))
        print((traceback.format_exc()))
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