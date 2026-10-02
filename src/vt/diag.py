"""Diagnóstico agregado (sin datos personales ni nombres): recuentos y percentiles para calibrar."""
from .db.conn import connect

Q = {
 "señales por tipo (kind,type) y total": "select kind,type,count(*),count(distinct company_hs_id) from signals group by 1,2 order by 3 desc",
 "señales por antigüedad (días) -> señales / empresas": """select case when occurred_at>now()-interval '7 days' then '0-7'
     when occurred_at>now()-interval '14 days' then '8-14' when occurred_at>now()-interval '30 days' then '15-30'
     when occurred_at>now()-interval '90 days' then '31-90' when occurred_at>now()-interval '365 days' then '91-365' else '>365' end b,
     count(*),count(distinct company_hs_id) from signals where points_raw<>0 group by 1 order by 1""",
 "empresas con señal de puntos en 30d": "select count(distinct company_hs_id) from signals where points_raw<>0 and occurred_at>now()-interval '30 days'",
 "contactos (total / excluidos / sin empresa asociada ya omitidos)": "select count(*),count(*) filter (where excluded) from contacts",
 "fit tier": "select fit_tier,count(*) from company_scores_daily where date=current_date group by 1 order by 1",
 "fit tier x status": "select fit_tier,status,count(*) from company_scores_daily s join companies c on c.hs_id=s.company_hs_id where s.date=current_date and fit_tier in ('A','B') group by 1,2 order by 1,3 desc",
 "intent: percentiles (0.5,0.9,0.99,max) y >0": "select percentile_cont(array[0.5,0.9,0.99]) within group (order by intent), max(intent), count(*) filter (where intent>0) from company_scores_daily where date=current_date",
 "engagement: percentiles y >0": "select percentile_cont(array[0.5,0.9,0.99]) within group (order by engagement), max(engagement), count(*) filter (where engagement>0) from company_scores_daily where date=current_date",
 "intent_tier": "select intent_tier,count(*) from company_scores_daily where date=current_date group by 1 order by 1",
 "prioridad": "select priority,count(*) from company_scores_daily where date=current_date group by 1 order by 1",
 "fit: percentiles": "select percentile_cont(array[0.1,0.5,0.9]) within group (order by fit), max(fit) from company_scores_daily where date=current_date",
 "proveedor sin casar (top 15 valores, solo valores del desplegable)": "select proveedor,count(*) from companies where proveedor is not null group by 1 order by 2 desc limit 15",
 "target_market (valores)": "select target_market,count(*) from companies group by 1 order by 2 desc limit 15",
}


def main():
    with connect() as conn:
        for title, sql in Q.items():
            print("\n##", title)
            try:
                for row in conn.execute(sql):
                    print("  ", row)
            except Exception as e:                      # un fallo no debe tapar el resto
                conn.rollback()
                print("   error:", type(e).__name__)


if __name__ == "__main__":
    main()
