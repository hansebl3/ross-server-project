import logging
from database import Database
from l2_builder import L2Builder
from clustering import SimilaritySearch

logger = logging.getLogger("Jobs")

def run_daily_job(db: Database, l2_builder: L2Builder):
    """
    Scans for unclustered L1s, finding 3+ related docs to form L2 insights.
    """
    logger.info("Running Daily L2 Clustering Job...")
    search_engine = SimilaritySearch(db)
    conn = db.get_connection()
    
    # 1. Get all Active L1s that are NOT yet in an L2
    query = """
        SELECT v.l1_id, v.source_uuid 
        FROM l1_versions v
        WHERE v.status = 'ACTIVE'
        AND NOT EXISTS (SELECT 1 FROM l2_members m WHERE m.l1_id = v.l1_id)
    """
    with conn.cursor() as cur:
        cur.execute(query)
        candidates = cur.fetchall() # list of (l1_id, source_uuid)
    
    logger.info(f"Found {len(candidates)} unclustered L1 candidates.")
    
    processed_ids = set()
    
    for l1_id, source_uuid in candidates:
        if l1_id in processed_ids:
            continue
            
        # Find neighbors
        neighbors = search_engine.find_related_l1(l1_id, limit=5, threshold=0.75)
        
        # Filter neighbors
        valid_neighbors = []
        for n in neighbors:
            n_id = n['l1_id']
            # We could check DB again here, but relying on candidates list partially
            valid_neighbors.append(n_id)
            
        if len(valid_neighbors) >= 2: # Seed + 2 neighbors = 3 docs
            cluster_ids = [l1_id] + valid_neighbors
            logger.info(f"Found cluster for {l1_id}: {len(cluster_ids)} items. Building L2.")
            try:
                l2_builder.build_l2_from_cluster(cluster_ids)
                processed_ids.add(l1_id)
                for nid in valid_neighbors:
                    processed_ids.add(nid)
            except Exception as e:
                logger.error(f"Failed to build L2 during daily job: {e}")
                
    logger.info("Daily Job Complete.")
