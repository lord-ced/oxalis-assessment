with enriched as (
    select * from {{ ref('int_sales_enriched') }}
),

daily_sales as (
    select
        date,
        store_id,
        region,
        customer_type,
        
        -- Aggregated metrics
        count(*) as transaction_count,
        sum(quantity_sold) as total_quantity,
        sum(gross_revenue) as gross_revenue,
        sum(discount_amount) as total_discount,
        sum(net_revenue) as net_revenue,
        avg(net_revenue) as avg_basket_size
        
    from enriched
    
    group by 
        date,
        store_id,
        region,
        customer_type
)

select * from daily_sales