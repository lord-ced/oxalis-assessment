with staged as (
    select * from {{ ref('stg_sales') }}
),

enriched as (
    select
        transaction_id,
        date,
        store_id,
        region,
        product_category,
        quantity_sold,
        unit_price,
        discount,
        customer_type,
        payment_method,
        
        -- Revenue calculations
        quantity_sold * unit_price as gross_revenue,
        quantity_sold * unit_price * coalesce(discount, 0) as discount_amount,
        quantity_sold * unit_price * (1 - coalesce(discount, 0)) as net_revenue,
        
        -- Date dimensions
        extract(year from date) as year,
        extract(month from date) as month,
        extract(dow from date) as day_of_week  -- 0 = Sunday, 6 = Saturday
        
    from staged
    
    -- Filter rows that can't participate in revenue math
    where quantity_sold is not null
      and unit_price is not null
      and date is not null
)

select * from enriched